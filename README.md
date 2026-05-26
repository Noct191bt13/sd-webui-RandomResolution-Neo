# Random Resolution Neo

Picks a random resolution from a list each batch.

## Features

- **Presets** — resolution lists saved as JSON files in `presets/`. SD1.5, SDXL, and Anima defaults are created on first launch.
- **Orientation filter** — restrict to vertical or horizontal only.
- **Weight modes** — equal, favor smaller, or favor larger.
- **Min/Max** — clamp dimensions.
- **HR fix** — adjusts upscale targets when hi-res is enabled.
- **RNG** — reseeds noise for the new resolution.

## Presets

Stored in `presets/<name>.json`. Create, save, and delete from the UI. Defaults are recreated if missing but can't be deleted.
