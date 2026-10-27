#!/usr/bin/env python3
"""Respaldo del Google Doc "Códigos para platinar Espacio UNAM".

1. Descarga el Doc público exportado como Markdown.
2. Lo sanea: quita imágenes incrustadas, cuentas de Instagram y enlaces de WhatsApp.
3. Extrae los códigos a datos/codigos-doc.csv.
4. Regenera las páginas de codigos/ y docs/codigos.json combinando el Doc y las aportaciones de la comunidad.

Uso:
    python3 scripts/sync_doc.py              # descarga y regenera
    python3 scripts/sync_doc.py --local F    # usa un .md ya descargado
    python3 scripts/sync_doc.py --solo-paginas  # solo regenera páginas (tras una aportación)

Solo usa la biblioteca estándar.
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
import urllib.request
from collections import defaultdict
from pathlib import Path

DOC_ID = "1o8UgQYTTjpBznUktuLK0WDKmX9nV4Ao2UIWs1MJQ2-s"
EXPORT_URL = f"https://docs.google.com/document/d/{DOC_ID}/export?format=md"
DOC_URL = f"https://docs.google.com/document/d/{DOC_ID}/edit"

RAIZ = Path(__file__).resolve().parent.parent
RESPALDO = RAIZ / "respaldo" / "documento.md"
CSV_DOC = RAIZ / "datos" / "codigos-doc.csv"
CSV_COMUNIDAD = RAIZ / "datos" / "comunidad.csv"
NO_CODIGOS = RAIZ / "datos" / "no-codigos.txt"
PAGINAS = RAIZ / "codigos"
JSON_WEB = RAIZ / "docs" / "codigos.json"

# Los códigos de Espacio UNAM usan 6 caracteres sin I, O, 0 ni 1.
ALFABETO = "A-HJ-NP-Z2-9"
RE_CODIGO = re.compile(rf"(?<![A-Za-z0-9])[{ALFABETO}]{{6}}(?![A-Za-z0-9])")
RE_PALABRA_MAYUS = re.compile(r"(?<![\w])[A-ZÁÉÍÓÚÑÜ]{2,}(?![\w])")
MESES = {"enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
         "agosto", "septiembre", "octubre", "noviembre", "diciembre"}
CAMPOS = ["codigo", "seccion", "subseccion", "etiqueta"]
CAMPOS_COMUNIDAD = ["codigo", "seccion", "subseccion", "etiqueta", "fecha", "issue"]


# ---------------------------------------------------------------- saneamiento

RE_IMAGEN_DATA = re.compile(r"^\[image\d+\]: <data:.*$", re.M)
RE_IMAGEN_REF = re.compile(r"!\[\]\[image\d+\]")
RE_INSTAGRAM_URL = re.compile(r"\[[^\]]*\]\([^)]*instagram\.com[^)]*\)?|(?:https?\\?:\\?/\\?/)?(?:www\\?\.\s*)?instagram\.com\S*", re.I)
RE_WHATSAPP_URL = re.compile(r"https?\\?:\\?/\\?/chat\.whatsapp\.com\S*", re.I)
RE_ARROBA = re.compile(r"(?<![\w.])@(?:\[[^\]]*\](?:\([^)]*\)?)?|[\w.\\*]+)")
RE_SOLO_RESTOS = re.compile(r"^[\s#*_\[\]()<>\-\\:|@🙌🏽🫰😝]*$")
# Inicio y fin del listado de Instagram ("Insta's pa seguirnos").
RE_LINEA_IG = re.compile(r"instagram\.com|^[\s#*_\[]*@\S", re.I)
RE_FIN_IG = re.compile(r"^#+\s*\**\s*Grupo de WhatsApp", re.I)
AVISO_IG = "> *Listado de cuentas de Instagram omitido por privacidad. Consúltalo en el Google Doc.*"


def sanear_linea(linea: str) -> str:
    original = linea
    linea = RE_WHATSAPP_URL.sub("[enlace de WhatsApp omitido]", linea)
    linea = RE_INSTAGRAM_URL.sub("", linea)
    linea = RE_ARROBA.sub("", linea)
    linea = re.sub(r"\[([^\]]*)\]\(\s*\)", r"\1", linea)  # enlaces que quedaron vacíos
    if linea != original and RE_SOLO_RESTOS.match(linea):
        return ""  # la línea solo contenía una cuenta personal
    return linea.rstrip()


def sanear(md: str) -> str:
    md = RE_IMAGEN_DATA.sub("", md)
    md = RE_IMAGEN_REF.sub("", md)
    lineas = md.splitlines()

    # Quita el bloque completo de cuentas de Instagram; dentro de él solo se conservan
    # las líneas que traen códigos (sin la cuenta).
    inicio = next((i for i, l in enumerate(lineas) if RE_LINEA_IG.search(l)), None)
    if inicio is not None:
        fin = next((j for j in range(inicio, len(lineas)) if RE_FIN_IG.match(lineas[j])), None)
        if fin is not None:
            conservadas = [l for l in map(sanear_linea, lineas[inicio:fin]) if RE_CODIGO.search(l)]
            lineas = lineas[:inicio] + ["", AVISO_IG, ""] + conservadas + [""] + lineas[fin:]

    salida = [sanear_linea(l) for l in lineas]
    texto = "\n".join(salida)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip() + "\n"


# ---------------------------------------------------------------- extracción

def limpiar(texto: str) -> str:
    texto = re.sub(r"\{#.*?\}", "", texto)
    texto = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", texto)
    texto = texto.replace("\\", "")
    texto = re.sub(r"[*_|]+", " ", texto)
    texto = re.sub(r"\s+", " ", texto)
    return texto.strip(" -–—:,.;·•")


def cargar_no_codigos() -> set[str]:
    if not NO_CODIGOS.exists():
        return set()
    return {l.strip().upper() for l in NO_CODIGOS.read_text(encoding="utf-8").splitlines()
            if l.strip() and not l.startswith("#")}


def es_grito(linea: str, inicio: int, fin: int) -> bool:
    """True si un token solo de letras está rodeado de palabras en mayúsculas que no son códigos."""
    vecinas = [m.group() for m in RE_PALABRA_MAYUS.finditer(linea)
               if 0 <= inicio - m.end() < 4 or 0 <= m.start() - fin < 4]
    return any(not RE_CODIGO.fullmatch(p) for p in vecinas)


def codigos_en(linea: str, excluidos: set[str]) -> list[re.Match]:
    validos = []
    for m in RE_CODIGO.finditer(linea):
        tok = m.group()
        if tok in excluidos:
            continue
        if tok.isalpha() and es_grito(linea, m.start(), m.end()):
            continue
        validos.append(m)
    return validos


def etiquetas(linea: str, matches: list[re.Match]) -> list[tuple[str, str]]:
    """Asocia cada código con su etiqueta.

    Dos formatos en el Doc:
      "**Carrera:** C1, C2"        -> la etiqueta va antes.
      "C1, C2 - **Nombre** C3 - X"  -> la etiqueta va después (Tocayo, Casi familia).
    """
    grupos: list[list[re.Match]] = []
    for m in matches:
        if grupos and limpiar(linea[grupos[-1][-1].end():m.start()]) == "":
            grupos[-1].append(m)
        else:
            grupos.append([m])
    prefijo = limpiar(linea[:grupos[0][0].start()])
    resultado = []
    if prefijo:  # etiqueta antes de cada grupo
        cortes = [0] + [g[-1].end() for g in grupos[:-1]]
        for g, desde in zip(grupos, cortes):
            et = limpiar(linea[desde:g[0].start()])
            resultado += [(m.group(), et) for m in g]
    else:  # etiqueta después de cada grupo
        for i, g in enumerate(grupos):
            hasta = grupos[i + 1][0].start() if i + 1 < len(grupos) else len(linea)
            et = limpiar(linea[g[-1].end():hasta])
            resultado += [(m.group(), et) for m in g]
    return [(c, et[:90]) for c, et in resultado]


# Nombres cortos para las secciones del Doc (se compara el inicio del título, sin acentos).
NOMBRES = [
    ("sedes", "Sedes"),
    ("cch", "CCH"),
    ("prepas", "Prepas"),
    ("enes", "ENES"),
    ("medallas secretas", "Medallas secretas"),
    ("pokemones que ya no existen", "Carreras que ya no existen o cambiaron de nombre"),
    ("apartado para el logro de tocayo", "Tocayo"),
    ("apartado casi familia", "Casi familia"),
    ("apartado a el logro de pastel compartido", "Pastel compartido"),
    ("apartado casi gemelos", "Casi gemelos"),
    ("apartado cazadora de mitos", "Cazadora de mitos"),
    ("apartado a compa de banca", "Compa de banca"),
    ("escuelas nacionales y otras entidades", "Escuelas nacionales y otras entidades"),
    ("no borren", "Anuncios de la comunidad"),
    ("chiqullos del bachillerato", "Anuncios de la comunidad"),
    ("me ayudaria mucho bachillerato", "Anuncios de la comunidad"),
    ("usen fotos de la web", "Otros"),
]


def nombre_seccion(titulo: str) -> str:
    base = slug(titulo).replace("-", " ")
    for prefijo, nombre in NOMBRES:
        if base.startswith(prefijo):
            return nombre
    return titulo[:70]


def extraer(md: str) -> list[dict]:
    excluidos = cargar_no_codigos()
    seccion, subseccion = "Inicio", ""
    filas, vistos = [], set()
    lineas = md.splitlines()
    for n, linea in enumerate(lineas):
        cab = re.match(r"^(#{1,3})\s+(.*)$", linea)
        matches = codigos_en(linea, excluidos)
        if cab and not matches:
            nivel, titulo = len(cab.group(1)), limpiar(cab.group(2))
            if not titulo or titulo.upper().startswith("DISCLAIMER"):
                continue
            if nivel <= 2 and titulo.lower() not in MESES:
                seccion, subseccion = nombre_seccion(titulo), ""
            else:
                subseccion = titulo[:70]
                # En el Doc las facultades de CU cuelgan del apartado FES.
                if seccion in ("FES", "Facultades de CU"):
                    seccion = "FES" if titulo.upper().startswith("FES") else "Facultades de CU"
            continue
        if not matches:
            continue
        # Medallas secretas: el código va solo y la descripción en la línea siguiente.
        siguiente = next((l for l in lineas[n + 1:n + 3] if l.strip()), "")
        descripcion = "" if siguiente.startswith("#") or RE_CODIGO.search(siguiente) else limpiar(siguiente)[:90]
        for codigo, et in etiquetas(linea, matches):
            et = et or descripcion
            fila = {"codigo": codigo, "seccion": seccion, "subseccion": subseccion, "etiqueta": et}
            clave = tuple(fila.values())
            if clave not in vistos:
                vistos.add(clave)
                filas.append(fila)
    return filas


# ---------------------------------------------------------------- páginas

def slug(texto: str) -> str:
    texto = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", texto.lower()).strip("-") or "otros"


def leer_csv(ruta: Path) -> list[dict]:
    if not ruta.exists():
        return []
    with ruta.open(encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def escribir_csv(ruta: Path, filas: list[dict], campos: list[str]) -> None:
    ruta.parent.mkdir(parents=True, exist_ok=True)
    with ruta.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos, lineterminator="\n")
        w.writeheader()
        w.writerows(filas)


def celda(texto: str) -> str:
    return texto.replace("|", "/") or "—"


def generar_paginas() -> None:
    doc = [dict(f, origen="doc") for f in leer_csv(CSV_DOC)]
    comunidad = [dict(f, origen="comunidad") for f in leer_csv(CSV_COMUNIDAD)]
    todas = doc + comunidad

    por_seccion: dict[str, list[dict]] = defaultdict(list)
    orden: list[str] = []
    for f in todas:
        if f["seccion"] not in por_seccion:
            orden.append(f["seccion"])
        por_seccion[f["seccion"]].append(f)

    PAGINAS.mkdir(exist_ok=True)
    for viejo in PAGINAS.glob("*.md"):
        viejo.unlink()

    indice = [
        "# Índice de códigos",
        "",
        "Generado automáticamente por `scripts/sync_doc.py`. **No edites estos archivos a mano**: "
        "se sobrescriben en cada sincronización. Para aportar un código abre un "
        "[issue de aportación](../../../issues/new?template=aporte-codigo.yml).",
        "",
        f"- Códigos del Google Doc: **{len(doc)}**",
        f"- Aportaciones vía GitHub: **{len(comunidad)}**",
        "",
        "| Sección | Códigos |",
        "|---|---:|",
    ]
    for sec in orden:
        nombre = f"{slug(sec)}.md"
        indice.append(f"| [{celda(sec)}]({nombre}) | {len(por_seccion[sec])} |")
        lineas = [f"# {sec}", "", "[← Índice](README.md)", ""]
        subs: dict[str, list[dict]] = defaultdict(list)
        for f in por_seccion[sec]:
            subs[f["subseccion"]].append(f)
        for sub, filas in subs.items():
            if sub:
                lineas += [f"## {sub}", ""]
            lineas += ["| Código | Etiqueta | Origen |", "|---|---|---|"]
            for f in filas:
                lineas.append(f"| `{f['codigo']}` | {celda(f['etiqueta'])} | {f['origen']} |")
            lineas.append("")
        (PAGINAS / nombre).write_text("\n".join(lineas), encoding="utf-8")
    (PAGINAS / "README.md").write_text("\n".join(indice) + "\n", encoding="utf-8")

    JSON_WEB.parent.mkdir(exist_ok=True)
    JSON_WEB.write_text(json.dumps(
        [{k: f[k] for k in CAMPOS + ["origen"]} for f in todas],
        ensure_ascii=False, separators=(",", ":")), encoding="utf-8")


# ---------------------------------------------------------------- main

def descargar() -> str:
    req = urllib.request.Request(EXPORT_URL, headers={"User-Agent": "espacio-unam-respaldo"})
    with urllib.request.urlopen(req, timeout=120) as r:
        if "markdown" not in r.headers.get("Content-Type", ""):
            raise RuntimeError("El Doc no devolvió Markdown (¿dejó de ser público?)")
        return r.read().decode("utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--local", type=Path, help="usar un .md exportado en lugar de descargar")
    ap.add_argument("--solo-paginas", action="store_true", help="solo regenerar codigos/ y docs/")
    args = ap.parse_args()

    if not args.solo_paginas:
        crudo = args.local.read_text(encoding="utf-8") if args.local else descargar()
        limpio = sanear(crudo)
        filas = extraer(limpio)
        # Protección ante vandalismo: si el Doc pierde más de la mitad de sus códigos, no se sobrescribe.
        previas = len(leer_csv(CSV_DOC))
        if previas and len(filas) < previas * 0.5:
            print(f"ABORTADO: el Doc pasó de {previas} a {len(filas)} códigos. "
                  "Posible borrado masivo; revisa el historial de versiones.", file=sys.stderr)
            return 2
        RESPALDO.parent.mkdir(exist_ok=True)
        RESPALDO.write_text(
            f"<!-- Copia saneada de {DOC_URL}\n"
            "     Generada automáticamente. Se omiten imágenes, cuentas de Instagram y enlaces de WhatsApp. -->\n\n"
            + limpio, encoding="utf-8")
        escribir_csv(CSV_DOC, filas, CAMPOS)
        print(f"{len(filas)} códigos extraídos del Doc")
    generar_paginas()
    return 0


if __name__ == "__main__":
    sys.exit(main())
