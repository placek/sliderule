# Slide Rule DXF Generator

This repo contains a single-purpose generator for slide rule layouts. The core logic lives in `rule.py`, which reads a YAML configuration and produces a DXF file containing linear or circular scales (ticks, labels, and scale names).

## Purpose of `rule.py`

`rule.py` is a config-driven DXF renderer for slide-rule scales. It:

- Loads a YAML file describing scales, tick density, labels, and layout.
- Compiles symbolic transform expressions (e.g., `log10(x)`) into Python callables.
- Draws linear or circular scales into DXF layers.
- Writes a DXF file and prints a short summary.

The file uses a `nix-shell` shebang to make it easy to run with the required Python dependencies.

## Usage

Basic run (uses the default config name):

```bash
./rule.py
```

Explicit config and output file:

```bash
./rule.py k-a-b-c-cf-ci-c-d-s-st-t.yaml -o k-a-b-c-cf-ci-c-d-s-st-t.dxf
```

The script prints a summary after writing the DXF:

- output file name
- layer names
- scale count and per-scale placement (radius or y offset)

## Configuration overview

The YAML file is the whole source of truth. It contains three top-level sections:

### 1) `global`
Defines overall geometry and DXF layer properties.

Key fields:

- `rule_length_mm`: linear baseline length used when drawing linear scales.
- `center`: `[x, y]` center point for circular layouts.
- `layers`: DXF layers and colors (e.g., `SLIDE`, `STATOR`).

### 2) `scales`
Defines individual scale types. Each scale entry supports:

- `transform`: expression mapping `x` to `[0, 1]`.
- `sections`: list of `[start, end]` ranges with tick definitions.
- `label_height`: tick height that gets a numeric label.
- `label_tilt`: label rotation (degrees) for circular layouts.
- `name_label`: scale name placement hints.
- `inherits`: copy another scale definition and override keys.

Tick definitions are `[[step, height_mm], ...]`. The height controls tick prominence and whether labels are drawn (only ticks matching `label_height` get labels).

### 3) `layout`
Defines the draw order and placement of each scale.

Each entry can include:

- `scale`: name of the scale definition from `scales`.
- `part`: DXF layer name (e.g., `SLIDE`, `STATOR`).
- `direction`: `up` or `down` (tick growth direction).
- `inverted`: `true` for right-to-left scales (CI, DI, etc.).
- `radius`: if set, draws a circular scale at this radius.
- `y_offset`: if set and `radius` is omitted, draws a linear scale at this y.

## Consequences and gotchas

- **Transforms are `eval`-compiled.** Only trusted configs should be used. Invalid or unsafe expressions can crash or do worse.
- **Transforms must map into `[0, 1]`.** Values outside this range are ignored, so scales can disappear if the transform is wrong.
- **Inversion affects naming.** If `inverted: true` and the scale name does not end in `I`, an `I` is appended in the rendered label.
- **Labeling is height-sensitive.** If `label_height` does not match any tick height, no numeric labels appear.
- **Overwrites output.** The `-o` target file is replaced without prompting.
- **Precision and rounding.** Tick positions are rounded to 5 decimals to avoid duplicate drawing; very fine steps can be skipped if they collide.

## File in this repo

- `k-a-b-c-cf-ci-c-d-s-st-t.yaml`: example configuration for a circular multi-scale rule.
- `k-a-b-c-cf-ci-c-d-s-st-t.dxf`: a sample output (may be overwritten if you use it as `-o`).

If you need a linear layout, set `y_offset` entries in `layout` and omit `radius` for those scales.
