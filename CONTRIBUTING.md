# Cómo contribuir

## Compartir códigos (sin saber programar)

1. Entra a **Issues → New issue → Aportar códigos**.
2. Elige la sección, escribe plantel/carrera (o nombre, apellido, día) y pega tus códigos.
3. Envía. Un bot los registra y cierra el issue en menos de un minuto.

Reglas: solo códigos, nada de Instagram, teléfonos ni correos; máximo 20 códigos por aporte; no hagas spam del mismo
código. Los aportes que no cumplan se eliminan.

## Corregir el extractor o el buscador

- Los archivos de `codigos/`, `respaldo/`, `datos/codigos-doc.csv` y `docs/codigos.json` **se generan solos**: no los
  edites a mano, cambia `scripts/sync_doc.py` y vuelve a correrlo.
- Si una palabra se cuela como código (por ejemplo `PASTEL`), agrégala a `datos/no-codigos.txt`.
- Si una sección queda con un nombre largo, agrégala a `NOMBRES` en `scripts/sync_doc.py`.
- Antes de abrir un pull request:

  ```bash
  python3 scripts/sync_doc.py
  git diff --stat
  ```

  Revisa que el número de códigos no baje sin motivo y que `respaldo/documento.md` no contenga `instagram.com` ni `@usuario`.

## Convivencia

Lee el [código de conducta](CODE_OF_CONDUCT.md). Esto es para conectar entre la comunidad, no para pelear.
