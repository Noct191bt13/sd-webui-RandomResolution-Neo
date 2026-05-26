# Random Resolution Neo

Forge Neo extension that picks a random resolution from a preset list each batch.

## Features

- **Presets** — named resolution lists saved as JSON files in `presets/`. Includes SD1.5, SDXL, and Anima defaults, auto-generated on first launch.
- **Weight modes** — Equal, Favor Smaller, or Favor Larger resolutions.
- **Min/Max filters** — clamp dimensions with step-64 granularity.
- **Auto model detection** — applies Anima validation (÷64, min 512, max 2048) when the WAN model is loaded.
- **HR fix** — adjusts upscale targets when hi-res is enabled.
- **RNG update** — reseeds noise correctly for the new resolution.

## Presets

Presets are stored in `presets/<name>.json`. Create, save, and delete them from the UI. Built-in defaults (SD1.5, SDXL, Anima) are regenerated if missing but can't be deleted.
