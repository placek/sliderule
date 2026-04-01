# Slide Rule DXF Generator

Config-driven DXF renderer for slide-rule scales. The main entry point is
`rule.py`, which reads a YAML file and writes a DXF containing linear or
circular scales (ticks, labels, and scale names).

## Repository contents

- `rule.py`: DXF generator (Python + ezdxf).
- `simple.yaml`: small circular example config.
- `k-a-b-c-cf-ci-c-d-s-st-t.yaml`: larger circular config.
- `k-a-b-c-cf-ci-c-d-s-st-t-linear.yaml`: linear variant of the above.
- `simple.dxf`: sample output from `simple.yaml`.
- `Makefile`: convenience targets to build the larger DXFs.

## Requirements

`rule.py` uses a `nix-shell` shebang for Python 3 + `ezdxf` + `pyyaml`.
If you are not using Nix, install those dependencies and run with `python3`.

## Usage

The script defaults to `sliderule.yaml`, which is not in this repo, so pass a
config path explicitly:

```bash
./rule.py simple.yaml -o simple.dxf
./rule.py k-a-b-c-cf-ci-c-d-s-st-t.yaml -o k-a-b-c-cf-ci-c-d-s-st-t.dxf
./rule.py k-a-b-c-cf-ci-c-d-s-st-t-linear.yaml -o k-a-b-c-cf-ci-c-d-s-st-t-linear.dxf
```

Build the two larger outputs with:

```bash
make
```

Clean generated DXFs:

```bash
make clean
```

After writing the DXF, the script prints a short summary of layers and scale
placements.

## Configuration format (YAML)

Top-level keys:

- `global`: overall geometry and DXF layers.
- `layout`: ordered scales grouped by part (e.g., `slide`, `stator`).

### `global`

- `type`: `circular` or `linear` (required).
- `center`: `[x, y]` center point for circular layouts.
- `rule_length_mm`: baseline length for linear layouts (defaults to 250.0).
- `layers`: mapping of DXF layers and colors (e.g., `SLIDE`, `STATOR`).

### `layout`

`layout` maps part names to lists of scale entries. Each part name is uppercased
and used as the DXF layer, so it should exist in `global.layers`.

Each scale entry supports:

- `name`: scale label.
- `offset`: radius (circular) or y-offset (linear).
- `direction`: `up` or `down` (tick growth direction).
- `inverted`: `true` to flip the scale left-to-right.
- `transform`: expression mapping `x` to `[0, 1]`.
- `sections`: list of `{start, end, ticks}` ranges.
- `label_height`: tick height that gets a numeric label.
- `label_tilt`: label rotation for circular layouts.
- `name_label`: `{angle_deg, linear_offset_x}` placement hints.
- `complement`: optional complement labeling:
  `{full_angle, label_height, text_height}`.

Tick definitions are `[[step, height_mm], ...]`. Height controls tick
prominence and whether labels are drawn (only ticks matching `label_height`
get numeric labels).

### Transform expressions

Transforms are compiled with `eval` and run against a small math namespace
(`log10`, `sin`, `cos`, `tan`, `rad`, `pi`, `e`, `sqrt`, `ln`, `abs`). Use only
trusted configs. The transform should map values into `[0, 1]`; values outside
that range are ignored.

## Limitations and gotchas

- **`inherits` is not implemented.** Some configs mention `inherits`, but
  `rule.py` does not resolve it. Duplicate the fields or use YAML anchors.
- **Output overwrites.** The `-o` target is replaced without prompting.
- **Precision.** Tick positions are rounded to 5 decimals to avoid duplicates;
  very fine steps can be skipped if they collide.
