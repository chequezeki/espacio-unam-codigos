# Códigos para platinar Espacio UNAM

Respaldo automático y espacio comunitario del documento colaborativo
[**Códigos para platinar Espacio UNAM**](https://docs.google.com/document/d/1o8UgQYTTjpBznUktuLK0WDKmX9nV4Ao2UIWs1MJQ2-s/edit),
hecho por y para toda la comunidad UNAM: CCH, prepas, FES, ENES, facultades de CU y demás entidades.

> El Doc sigue siendo el lugar principal. Este repositorio existe para que **nada se pierda** cuando alguien borra
> secciones, y para que haya una forma ordenada de buscar y compartir códigos.

## Cómo usarlo

| Quiero… | Ve a |
|---|---|
| Buscar un código por carrera, plantel, nombre o apellido | **[Buscador](https://jaguaror.github.io/espacio-unam-codigos/)** (GitHub Pages) |
| Ver los códigos ordenados por sección | [`codigos/`](codigos/README.md) |
| Compartir mis códigos | [Abrir un aporte](../../issues/new?template=aporte-codigo.yml) (necesitas cuenta de GitHub, es gratis) |
| Reportar un código que no sirve o pedir que se retire un dato | [Abrir un reporte](../../issues/new?template=reporte.yml) |
| Recuperar algo que borraron del Doc | [`respaldo/documento.md`](respaldo/documento.md) y su [historial](../../commits/main/respaldo/documento.md) |
| Descargar todos los datos | [`datos/codigos-doc.csv`](datos/codigos-doc.csv) y [`datos/comunidad.csv`](datos/comunidad.csv) |

## Cómo funciona

```
Google Doc ──(cada 15 min)──> scripts/sync_doc.py ──> respaldo/documento.md   copia saneada del Doc
                                                 ├──> datos/codigos-doc.csv   códigos extraídos
Issue "Aportar códigos" ──> scripts/aporte.py ───┼──> datos/comunidad.csv     aportes vía GitHub
                                                 └──> codigos/*.md + docs/codigos.json (índice y buscador)
```

- **Sincronización:** el workflow [`sincronizar.yml`](.github/workflows/sincronizar.yml) descarga el Doc cada 15 minutos.
  Si cambió, guarda un commit; así cada versión queda en el historial de Git.
- **Protección contra borrados:** si el Doc pierde más de la mitad de sus códigos de golpe, la sincronización se
  detiene en lugar de sobrescribir el respaldo.
- **Aportes:** el workflow [`aporte.yml`](.github/workflows/aporte.yml) valida los códigos del formulario, los agrega
  a `datos/comunidad.csv`, responde y cierra el issue.

## Privacidad

El respaldo **omite** imágenes, cuentas de Instagram y enlaces a grupos de WhatsApp que aparecen en el Doc.
Las secciones Tocayo, Casi familia y Casi gemelos contienen solo primer nombre, primer apellido o día de
cumpleaños junto al código, tal como la comunidad los publicó.
Si quieres que se retire algo tuyo, abre un [reporte](../../issues/new?template=reporte.yml) sin repetir el dato.

## Estructura

```
respaldo/documento.md      copia saneada del Doc (generada)
datos/codigos-doc.csv      código, sección, subsección, etiqueta (generado)
datos/comunidad.csv        aportes de GitHub (+ fecha e issue)
datos/no-codigos.txt       palabras que NO son códigos (editable)
codigos/                   una página por sección (generada, no editar a mano)
docs/                      buscador web (GitHub Pages)
scripts/                   sync_doc.py y aporte.py (solo biblioteca estándar de Python)
```

## Ejecutarlo localmente

```bash
python3 scripts/sync_doc.py            # descarga el Doc y regenera todo
python3 scripts/sync_doc.py --solo-paginas
```

Para mejorar el extractor, la página o la documentación, lee [CONTRIBUTING.md](CONTRIBUTING.md).

---

Gracias a Etmis, a Runix y a todas las personas que mantienen el Doc vivo. Este proyecto no está afiliado
oficialmente a la UNAM ni a Espacio UNAM.
