#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.ezdxf python3Packages.pyyaml

import sys
import math
import yaml
import ezdxf
from ezdxf.enums import TextEntityAlignment


# ============================================================
#  Transform expression compiler
# ============================================================

_TRANSFORM_NAMESPACE = {
    'math':   math,
    'log10':  math.log10,
    'sin':    math.sin,
    'cos':    math.cos,
    'tan':    math.tan,
    'rad':    math.radians,
    'pi':     math.pi,
    'e':      math.e,
    'sqrt':   math.sqrt,
    'ln':     math.log,
    'abs':    abs,
}


def compile_transform(expr: str):
    """Compile a YAML transform string into a callable(x) -> float."""
    code = compile(expr, f'<transform: {expr}>', 'eval')

    def fn(x, _code=code, _ns=_TRANSFORM_NAMESPACE):
        return eval(_code, _ns, {'x': x})

    return fn


# ============================================================
#  SlideRuleScale — draws one scale
# ============================================================

class SlideRuleScale:
    """Generic slide-rule scale driven entirely by config data."""

    def __init__(self, scale_cfg, *, layer=None, rule_length=250.0):
        self.rule_length = rule_length
        self.direction = scale_cfg.get('direction', 'up')
        self.inverted = scale_cfg.get('inverted', False)
        self.layer = layer
        self.drawn_ticks = set()

        # --- transform ---
        self._transform_fn = compile_transform(scale_cfg['transform'])

        # --- sections ---
        self.sections = []
        for sec in scale_cfg['sections']:
            self.sections.append({
                'start': float(sec['start']),
                'end':   float(sec['end']),
                'ticks': [(float(t[0]), float(t[1])) for t in sec['ticks']],
            })

        # --- labelling ---
        self.label_height = float(scale_cfg.get('label_height', 8.0))
        self.label_tilt   = float(scale_cfg.get('label_tilt', 0.0))

        name_label = scale_cfg.get('name_label', {})
        self.name_angle_deg   = float(name_label.get('angle_deg', 83.0))
        self.linear_offset_x  = float(name_label.get('linear_offset_x', -5.0))

        # --- complement labels (e.g. cos on a sin scale) ---
        comp = scale_cfg.get('complement', None)
        if comp:
            self.complement_angle = float(comp['full_angle'])
            self.complement_label_height = float(
                comp.get('label_height', self.label_height))
            self.complement_text_height = float(
                comp.get('text_height', 2.0))
        else:
            self.complement_angle = None

        # --- display name ---
        self.name = scale_cfg['name']
        if self.inverted and not self.name.endswith('I'):
            self.name += 'I'

    # ---------- transform ----------

    def transform(self, x):
        return self._transform_fn(x)

    # ---------- DXF helpers ----------

    def _dxfattribs(self, extra=None):
        a = {}
        if self.layer:
            a['layer'] = self.layer
        if extra:
            a.update(extra)
        return a

    # ---------- tick iteration ----------

    def _iter_ticks(self):
        for section in self.sections:
            start = section['start']
            end   = section['end']
            for step, height in section['ticks']:
                num_ticks = int(round((end - start) / step))
                for i in range(num_ticks + 1):
                    x = start + (i * step)
                    x_rounded = round(x, 5)
                    if x_rounded > end:
                        continue
                    if x_rounded in self.drawn_ticks:
                        continue
                    mapped_val = self.transform(x)
                    if self.inverted:
                        mapped_val = 1.0 - mapped_val
                    if -0.00001 <= mapped_val <= 1.00001:
                        yield x_rounded, mapped_val, height

    def _mark_drawn(self, x_rounded):
        self.drawn_ticks.add(x_rounded)

    # ==========================================================
    #  Linear drawing
    # ==========================================================

    def draw(self, msp, y_offset=0.0):
        y_mult = 1.0 if self.direction == 'up' else -1.0
        text_align = (TextEntityAlignment.BOTTOM_CENTER
                      if self.direction == 'up'
                      else TextEntityAlignment.TOP_CENTER)
        comp_align = (TextEntityAlignment.TOP_CENTER
                      if self.direction == 'up'
                      else TextEntityAlignment.BOTTOM_CENTER)

        self._draw_linear_name(msp, y_offset, y_mult)

        for x_rounded, mapped_val, height in self._iter_ticks():
            pos_x = mapped_val * self.rule_length
            self._draw_linear_tick(msp, pos_x, y_offset, height, y_mult)
            if height == self.label_height:
                self._draw_linear_label(msp, pos_x, y_offset, height,
                                        y_mult, text_align, x_rounded)
            if (self.complement_angle is not None
                    and height >= self.complement_label_height):
                self._draw_linear_complement(msp, pos_x, y_offset,
                                             y_mult, comp_align, x_rounded)
            self._mark_drawn(x_rounded)

        self._draw_linear_baseline(msp, y_offset)

    def _draw_linear_name(self, msp, y_offset, y_mult):
        msp.add_text(
            self.name, dxfattribs=self._dxfattribs({'height': 3.0})
        ).set_placement(
            (self.linear_offset_x, y_offset + (2.0 * y_mult)),
            align=TextEntityAlignment.MIDDLE_RIGHT,
        )

    def _draw_linear_tick(self, msp, pos_x, y_offset, height, y_mult):
        msp.add_line(
            (pos_x, y_offset),
            (pos_x, y_offset + (height * y_mult)),
            dxfattribs=self._dxfattribs(),
        )

    def _draw_linear_label(self, msp, pos_x, y_offset, height,
                           y_mult, text_align, x_rounded):
        label_text = f"{x_rounded:g}"
        msp.add_text(
            label_text, dxfattribs=self._dxfattribs({'height': 2.5})
        ).set_placement(
            (pos_x, y_offset + ((height + 0.5) * y_mult)),
            align=text_align,
        )

    def _draw_linear_baseline(self, msp, y_offset):
        msp.add_line(
            (0, y_offset), (self.rule_length, y_offset),
            dxfattribs=self._dxfattribs(),
        )

    def _draw_linear_complement(self, msp, pos_x, y_offset,
                                y_mult, comp_align, x_rounded):
        """Draw a complement-angle label on the opposite side of the baseline."""
        comp_val = round(self.complement_angle - x_rounded, 5)
        if comp_val <= 0:
            return
        label_text = f"{comp_val:g}"
        msp.add_text(
            label_text, dxfattribs=self._dxfattribs({
                'height': self.complement_text_height,
            })
        ).set_placement(
            (pos_x, y_offset - (0.5 * y_mult)),
            align=comp_align,
        )

    # ==========================================================
    #  Circular drawing
    # ==========================================================

    def draw_circular(self, msp, radius, center_x=0.0, center_y=0.0):
        y_mult = 1.0 if self.direction == 'up' else -1.0

        self._draw_circular_baseline(msp, radius, center_x, center_y)
        self._draw_circular_name(msp, radius, center_x, center_y, y_mult)

        for x_rounded, mapped_val, height in self._iter_ticks():
            if abs(mapped_val - 1.0) < 0.00001:
                continue

            angle_deg, angle_rad = self._mapped_val_to_angle(mapped_val)

            self._draw_circular_tick(msp, radius, center_x, center_y,
                                     height, y_mult, angle_rad)
            if height == self.label_height:
                self._draw_circular_label(msp, radius, center_x, center_y,
                                          height, y_mult, angle_deg,
                                          angle_rad, x_rounded)
            if (self.complement_angle is not None
                    and height >= self.complement_label_height):
                self._draw_circular_complement(msp, radius, center_x,
                                               center_y, y_mult,
                                               angle_deg, angle_rad,
                                               x_rounded)
            self._mark_drawn(x_rounded)

    # -- circular helpers --

    @staticmethod
    def _mapped_val_to_angle(mapped_val):
        angle_deg = 90.0 - (mapped_val * 360.0)
        angle_rad = math.radians(angle_deg)
        return angle_deg, angle_rad

    @staticmethod
    def _point_on_circle(center_x, center_y, r, angle_rad):
        return (center_x + r * math.cos(angle_rad),
                center_y + r * math.sin(angle_rad))

    def _draw_circular_baseline(self, msp, radius, center_x, center_y):
        msp.add_circle(
            (center_x, center_y), radius,
            dxfattribs=self._dxfattribs(),
        )

    def _max_tick_height(self):
        return max(h for sec in self.sections for _, h in sec['ticks'])

    def _draw_circular_name(self, msp, radius, center_x, center_y, y_mult):
        name_angle_rad = math.radians(self.name_angle_deg)
        name_radius = radius + ((self._max_tick_height() + 1.5) * y_mult)
        text_rot = self.name_angle_deg - 90.0

        tx, ty = self._point_on_circle(center_x, center_y,
                                       name_radius, name_angle_rad)
        msp.add_text(
            self.name,
            dxfattribs=self._dxfattribs({
                'height': 3.0, 'rotation': text_rot,
            }),
        ).set_placement((tx, ty), align=TextEntityAlignment.MIDDLE_CENTER)

    def _draw_circular_tick(self, msp, radius, center_x, center_y,
                            height, y_mult, angle_rad):
        x0, y0 = self._point_on_circle(center_x, center_y,
                                       radius, angle_rad)
        r1 = radius + (height * y_mult)
        x1, y1 = self._point_on_circle(center_x, center_y,
                                       r1, angle_rad)
        msp.add_line((x0, y0), (x1, y1), dxfattribs=self._dxfattribs())

    def _draw_circular_label(self, msp, radius, center_x, center_y,
                             height, y_mult, angle_deg, angle_rad,
                             x_rounded):
        label_text = f"{x_rounded:g}"
        text_radius = radius + ((height + 1.5) * y_mult)
        tx, ty = self._point_on_circle(center_x, center_y,
                                       text_radius, angle_rad)
        text_rot = angle_deg - 90 + self.label_tilt
        msp.add_text(
            label_text,
            dxfattribs=self._dxfattribs({'height': 2.5, 'rotation': text_rot}),
        ).set_placement((tx, ty), align=TextEntityAlignment.MIDDLE_CENTER)

    def _draw_circular_complement(self, msp, radius, center_x, center_y,
                                  y_mult, angle_deg, angle_rad, x_rounded):
        """Draw a complement-angle label on the opposite side of the baseline."""
        comp_val = round(self.complement_angle - x_rounded, 5)
        if comp_val <= 0:
            return
        label_text = f"{comp_val:g}"
        text_radius = radius - (1.5 * y_mult)
        tx, ty = self._point_on_circle(center_x, center_y,
                                       text_radius, angle_rad)
        text_rot = angle_deg - 90 + self.label_tilt
        msp.add_text(
            label_text,
            dxfattribs=self._dxfattribs({
                'height': self.complement_text_height,
                'rotation': text_rot,
            }),
        ).set_placement((tx, ty), align=TextEntityAlignment.MIDDLE_CENTER)


# ============================================================
#  Main: load YAML → build scales → render DXF
# ============================================================

def load_config(path):
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def build_and_render(cfg, output_file='output.dxf'):
    g = cfg['global']
    rule_type = g.get('type', None)
    if rule_type not in ('circular', 'linear'):
        raise ValueError(
            f"global.type must be 'circular' or 'linear', got {rule_type!r}"
        )

    layers_cfg = g.get('layers', {})
    layout     = cfg['layout']

    # Type-specific geometry
    if rule_type == 'linear':
        rule_length = g.get('rule_length_mm', 250.0)
    else:
        center = tuple(g.get('center', [0.0, 0.0]))
        rule_length = 250.0

    # --- DXF document ---
    doc = ezdxf.new(dxfversion='R2010')
    msp = doc.modelspace()

    for layer_name, layer_props in layers_cfg.items():
        doc.layers.add(layer_name,
                       dxfattribs={'color': layer_props.get('color', 7)})

    # --- walk the layout ---
    drawn_count = 0
    summary_lines = []

    for part_name, entries in layout.items():
        layer = part_name.upper()

        for entry in entries:
            offset = float(entry['offset'])

            scale_obj = SlideRuleScale(
                entry, layer=layer, rule_length=rule_length,
            )

            if rule_type == 'circular':
                scale_obj.draw_circular(msp, radius=offset,
                                        center_x=center[0],
                                        center_y=center[1])
                summary_lines.append(
                    f"  {scale_obj.name:4s}  {layer:7s}  R={offset:.1f}")
            else:
                scale_obj.draw(msp, y_offset=offset)
                summary_lines.append(
                    f"  {scale_obj.name:4s}  {layer:7s}  y={offset:.1f}")

            drawn_count += 1

    # --- save ---
    doc.saveas(output_file)

    # --- summary ---
    print(f"Generated {output_file}  ({rule_type})")
    print(f"Layers: {', '.join(layers_cfg.keys())}")
    print(f"Scales drawn: {drawn_count}")
    for line in summary_lines:
        print(line)


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Slide-rule DXF generator')
    parser.add_argument('config', nargs='?', default='sliderule.yaml',
                        help='YAML config file (default: sliderule.yaml)')
    parser.add_argument('-o', '--output', default='output.dxf',
                        help='Output DXF file (default: output.dxf)')
    args = parser.parse_args()

    cfg = load_config(args.config)
    build_and_render(cfg, args.output)
