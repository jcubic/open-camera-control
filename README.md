# open-camera-control

A GTK application to control camera settings (ISO, aperture, shutter speed, white balance) via gphoto2. Keeps a persistent USB session so changing settings doesn't interrupt the camera's live view.

## Requirements

- Python 3.10+
- libgphoto2 (system package)
- GTK 3 + PyGObject (system package)
- A gphoto2-compatible camera connected via USB

### System dependencies (Fedora)

```bash
sudo dnf install libgphoto2 gtk3 gobject-introspection-devel cairo-gobject-devel
```

### System dependencies (Debian/Ubuntu)

```bash
sudo apt install libgphoto2-6 gir1.2-gtk-3.0 python3-gi libgirepository1.0-dev
```

## Installation

```bash
pip install open-camera-control
```

Or install from source:

```bash
git clone https://github.com/jcubic/open-camera-control.git
cd open-camera-control
pip install -e .
```

## Usage

Connect your camera via USB and run:

```bash
camera-control
```

The application opens a window with a camera selector at the top and two tabs (Photo / Video) below.

### Camera selector

The top bar shows all detected cameras in a dropdown. Select a camera and click **Connect** to start controlling it. The button turns green when connected and changes to **Disconnect**. Disconnecting preserves the camera's live view. Use the refresh button to re-scan for newly connected cameras.

### Settings tabs

Each tab (Photo / Video) contains:

- **ISO** — slider + text input
- **Aperture** — slider + text input
- **Shutter Speed** — slider + text input
- **White Balance** — preset dropdown + Kelvin slider + text input

Moving a slider updates the text input. Type a value directly into the text input and press Enter — it will snap to the nearest valid value. Click **Apply** to send all changes to the camera at once.

For white balance, selecting a preset from the dropdown sets the Kelvin value. Moving the Kelvin slider or typing a value switches the dropdown to "Custom".

## Configuration

On first run, the app creates `~/.open-camera-control/config.json` with default white balance presets:

```json
{
  "white_balance_presets": {
    "Daylight": 5600,
    "Cloudy": 6500,
    "Shade": 7500,
    "Tungsten": 3200,
    "Fluorescent": 4000,
    "Flash": 5400
  },
  "kelvin_range": {
    "min": 2500,
    "max": 10000,
    "step": 100
  }
}
```

Edit this file to add, remove, or rename white balance presets, or to change the Kelvin slider range.

## Camera model support

Different camera models expose different gphoto2 widget names for the same settings. The app ships with per-model JSON mapping files in `src/opencameracontrol/models/`.

### Supported models

- Nikon D780
- Fuji Fujifilm X-Pro3

### Using an unsupported camera

If your camera model is not yet supported, run the detection tool:

```bash
camera-control-detect
```

This connects to your camera, lists all available widgets, and outputs a suggested JSON mapping. You can then either:

**Option A — Personal use:** Add the mapping to your `~/.open-camera-control/config.json`:

```json
{
  "models": {
    "My Camera Model": {
      "video_widgets": true,
      "photo": {
        "shutterspeed": "shutterspeed2"
      }
    }
  }
}
```

If a model is found in the user config, the bundled model file is not used.

**Option B — Contribute:** Save the JSON output as a model file and submit a pull request (see Contributing below).

## Contributing camera models

To add support for a new camera model:

1. Connect your camera via USB
2. Run `camera-control-detect`
3. Review the suggested widget mapping — the tool guesses based on widget labels, but you should verify:
   - The widget is **not read-only** (the tool marks these)
   - The choices look correct for that setting
   - For shutter speed, prefer `shutterspeed2` over `shutterspeed` if both exist (the former uses `1/125` format and is usually writable)
4. Save the JSON output to `src/opencameracontrol/models/<normalized_name>.json`
5. Submit a pull request

### Model file format

Model files only need to specify settings that differ from the defaults. The default widget names are:

| Setting      | Default widget name |
|--------------|---------------------|
| iso          | `iso`               |
| aperture     | `f-number`          |
| shutterspeed | `shutterspeed`      |
| whitebalance | `whitebalance`      |

For cameras with separate video widgets (e.g., Nikon DSLRs), set `"video_widgets": true`. This auto-generates video widget names by adding the `movie` prefix (e.g., `movieiso`, `movief-number`). Add a `"video"` section only for video widgets that don't follow this pattern.

**Minimal model file** (camera uses all default widget names, same for photo and video):

```json
{
    "model": "Fuji Fujifilm X-Pro3"
}
```

**Model with overrides** (photo shutterspeed differs, camera has separate video widgets):

```json
{
    "model": "Nikon DSC D780",
    "video_widgets": true,
    "photo": {
        "shutterspeed": "shutterspeed2"
    }
}
```

The filename is the model name normalized to lowercase with special characters replaced by underscores (e.g., `"Nikon DSC D780"` becomes `nikon_dsc_d780.json`).

## How it works

The app uses [python-gphoto2](https://github.com/jim-easterbrook/python-gphoto2) to maintain a persistent PTP/USB session with the camera — equivalent to running `gphoto2 --shell`. This means settings can be changed freely without the camera dropping live view or reconnecting, which is a known issue with individual `gphoto2` CLI commands.

## License

Copyright (c) 2026 [Jakub T. Jankiewicz](https://jakub.jankiewicz.org/)

Released under the MIT License. See [LICENSE](https://github.com/jcubic/open-camera-control/blob/master/LICENSE) for details.
