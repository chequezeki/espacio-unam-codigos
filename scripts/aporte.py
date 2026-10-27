#!/usr/bin/env python3
"""Registra una aportación hecha con el formulario de issue "Aportar códigos".

Lee el cuerpo del issue de la variable de entorno ISSUE_BODY (nunca se interpola en la shell),
valida los códigos y los agrega a datos/comunidad.csv. Escribe el resumen para el comentario
del bot en la ruta indicada por RESUMEN (por defecto, stdout).

Variables: ISSUE_BODY, ISSUE_NUMBER, RESUMEN (opcional).
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sync_doc import (CAMPOS_COMUNIDAD, CSV_COMUNIDAD, CSV_DOC, RE_CODIGO,  # noqa: E402
                      escribir_csv, leer_csv, limpiar)

SECCIONES_VALIDAS = {
    "CCH", "Prepas", "ENES", "FES", "Facultades de CU", "Escuelas nacionales y otras entidades",
    "Medallas secretas", "Tocayo", "Casi familia", "Casi gemelos", "Pastel compartido",
    "Compa de banca", "Cazadora de mitos", "Otros",
}


def campos_formulario(cuerpo: str) -> dict[str, str]:
    """Los issue forms generan bloques '### Título\\n\\nvalor'."""
    partes = re.split(r"^### +(.+)$", cuerpo, flags=re.M)
    return {partes[i].strip(): partes[i + 1].strip() for i in range(1, len(partes) - 1, 2)}


def main() -> int:
    cuerpo = os.environ.get("ISSUE_BODY", "")
    issue = os.environ.get("ISSUE_NUMBER", "")
    datos = campos_formulario(cuerpo)

    seccion = datos.get("Sección", "").strip()
    if seccion not in SECCIONES_VALIDAS:
        seccion = "Otros"
    subseccion = limpiar(datos.get("Plantel, facultad o mes", "").replace("_No response_", ""))[:70]
    etiqueta = limpiar(datos.get("Carrera, nombre, apellido o día", "").replace("_No response_", ""))[:90]
    texto = datos.get("Códigos", "").upper()
    # Quita restos peligrosos o de formato y se queda solo con códigos válidos.
    codigos = list(dict.fromkeys(RE_CODIGO.findall(re.sub(r"[^A-Z0-9]+", " ", texto))))[:20]

    existentes = leer_csv(CSV_COMUNIDAD)
    ya = {(f["codigo"], f["seccion"], f["etiqueta"]) for f in existentes}
    ya |= {(f["codigo"], f["seccion"], f["etiqueta"]) for f in leer_csv(CSV_DOC)}
    nuevos = [c for c in codigos if (c, seccion, etiqueta) not in ya]

    hoy = date.today().isoformat()
    existentes += [{"codigo": c, "seccion": seccion, "subseccion": subseccion,
                    "etiqueta": etiqueta, "fecha": hoy, "issue": issue} for c in nuevos]
    escribir_csv(CSV_COMUNIDAD, existentes, CAMPOS_COMUNIDAD)

    if nuevos:
        resumen = (f"¡Gracias! Se agregaron {len(nuevos)} código(s) a **{seccion}**"
                   f"{' / ' + subseccion if subseccion else ''}: "
                   + ", ".join(f"`{c}`" for c in nuevos)
                   + "\n\nAparecerán en el índice y en el buscador en unos minutos.")
    elif codigos:
        resumen = "Estos códigos ya estaban registrados con la misma sección y etiqueta. ¡Gracias de todos modos!"
    else:
        resumen = ("No encontré códigos válidos. Recuerda que tienen 6 caracteres (letras y números, "
                   "sin I, O, 0 ni 1). Puedes editar el issue y reabrirlo.")

    salida = os.environ.get("RESUMEN")
    if salida:
        Path(salida).write_text(resumen, encoding="utf-8")
    else:
        print(resumen)
    return 0 if nuevos else 1


if __name__ == "__main__":
    sys.exit(main())
