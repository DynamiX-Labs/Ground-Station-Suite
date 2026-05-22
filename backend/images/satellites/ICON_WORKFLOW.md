# Satellite Icon Workflow

Use this workflow when adding satellite icons from user-provided source links + NORAD IDs.

## Input format

`NORAD_ID | SATELLITE_NAME | IMAGE_URL`

Process all provided entries in one batch unless the user explicitly asks otherwise.

## Required workflow per satellite

1. Download the source image from the provided URL.
2. Create a clean transparent icon from the source.
3. Save/update these files:
   - `backend/images/satellites/full/{NORAD}.png` (transparent master/fallback)
   - `backend/images/satellites/64/{NORAD}.png`
   - `backend/images/satellites/128/{NORAD}.png`
   - `backend/images/satellites/256/{NORAD}.png`
4. Composition requirements:
   - Tight crop to foreground content bounds.
   - Center-fit in square preset canvases.
   - Minimal padding.
   - Keep readability at small sizes (`64x64`).
5. Preserve current UI behavior:
   - Keep spinner while image is loading.
   - Keep blank result if image is missing.
   - Do not introduce a fallback glyph for missing images.
6. Update `backend/images/satellites/ATTRIBUTION.md` for each icon:
   - Source URL.
   - Short processing note.
   - List generated preset files (`64/`, `128/`, `256/`).
7. Run frontend build verification after processing:
   - `cd frontend && npm run build`
   - Report pass/fail and relevant warnings.
8. Do not start frontend/backend dev servers unless explicitly requested in the current turn.

## Notes

- Prefer deterministic local image processing (background removal + trim + center-fit) so results are repeatable.
- Replace an existing icon for a NORAD ID when a new source is explicitly provided.

## Batch automation (no LLM calls)

Use `backend/scripts/process_satellite_icons.py` for deterministic batch processing.

Dry-run (report only, no writes):

```bash
cd backend
./venv/bin/python scripts/process_satellite_icons.py
```

Apply changes to all NORAD-named source images:

```bash
cd backend
./venv/bin/python scripts/process_satellite_icons.py --apply
```

Process only specific NORAD IDs:

```bash
cd backend
./venv/bin/python scripts/process_satellite_icons.py --norad 43700 7530 --apply
```
