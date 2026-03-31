#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.ezdxf

import ezdxf
import math
from ezdxf.enums import TextEntityAlignment

RULE_LENGTH = 250.0

# ==========================================
# Layer names
# ==========================================
LAYER_SLIDE   = "SLIDE"    # B, CI, C, CF  — the sliding part
LAYER_STATOR  = "STATOR"   # A, D, S, ST, T, K, L — fixed parts

class SlideRuleScale:
    """Base class for all slide rule scales."""
    def __init__(self, direction='up', inverted=False, layer=None):
        self.sections = []
        self.drawn_ticks = set()
        self.direction = direction
        self.inverted = inverted
        self.layer = layer  # DXF layer name

        self.name = self.__class__.__name__.replace("Scale", "")
        if self.inverted and not self.name.endswith('I'):
            self.name += "I"

    def transform(self, x):
        raise NotImplementedError

    def _dxfattribs(self, extra=None):
        a = {}
        if self.layer:
            a['layer'] = self.layer
        if extra:
            a.update(extra)
        return a

    def draw(self, msp, y_offset=0.0):
        """Draws the scale linearly."""
        y_mult = 1.0 if self.direction == 'up' else -1.0
        text_align = TextEntityAlignment.BOTTOM_CENTER if self.direction == 'up' else TextEntityAlignment.TOP_CENTER

        msp.add_text(self.name, dxfattribs=self._dxfattribs({'height': 3.0})).set_placement(
            (-5.0, y_offset + (2.0 * y_mult)),
            align=TextEntityAlignment.MIDDLE_RIGHT
        )
        for section in self.sections:
            start = section['start']
            end = section['end']
            for step, height in section['ticks']:
                num_ticks = int(round((end - start) / step))
                for i in range(num_ticks + 1):
                    x = start + (i * step)
                    x_rounded = round(x, 5)
                    if x_rounded > end:
                        continue
                    if x_rounded not in self.drawn_ticks:
                        mapped_val = self.transform(x)
                        if self.inverted:
                            mapped_val = 1.0 - mapped_val
                        if -0.00001 <= mapped_val <= 1.00001:
                            pos_x = mapped_val * RULE_LENGTH
                            msp.add_line((pos_x, y_offset), (pos_x, y_offset + (height * y_mult)),
                                         dxfattribs=self._dxfattribs())
                            if height == 8.0:
                                label_text = f"{x_rounded:g}"
                                msp.add_text(label_text, dxfattribs=self._dxfattribs({'height': 2.5})).set_placement(
                                    (pos_x, y_offset + ((height + 0.5) * y_mult)),
                                    align=text_align
                                )
                            self.drawn_ticks.add(x_rounded)

        msp.add_line((0, y_offset), (RULE_LENGTH, y_offset), dxfattribs=self._dxfattribs())

    def draw_circular(self, msp, radius, center_x=0.0, center_y=0.0):
        """Draws the scale radially around a center point."""
        y_mult = 1.0 if self.direction == 'up' else -1.0

        msp.add_circle((center_x, center_y), radius, dxfattribs=self._dxfattribs())

        # Label sits just clockwise of the scale start (mapped_val=0 -> 90 deg).
        # 'Right of the start' means a few degrees clockwise, i.e. angle slightly < 90 deg.
        name_angle_deg = 83.0          # 90 - 7 deg offset clockwise
        name_angle_rad = math.radians(name_angle_deg)
        name_radius    = radius + (12.0 * y_mult)
        # Rotate text tangentially so it reads naturally along the arc.
        text_rot = name_angle_deg - 90.0   # = -7 deg
        msp.add_text(self.name, dxfattribs=self._dxfattribs({'height': 3.0, 'rotation': text_rot})).set_placement(
            (center_x + name_radius * math.cos(name_angle_rad),
             center_y + name_radius * math.sin(name_angle_rad)),
            align=TextEntityAlignment.MIDDLE_CENTER
        )

        for section in self.sections:
            start = section['start']
            end = section['end']
            for step, height in section['ticks']:
                num_ticks = int(round((end - start) / step))
                for i in range(num_ticks + 1):
                    x = start + (i * step)
                    x_rounded = round(x, 5)

                    if x_rounded > end:
                        continue
                    if x_rounded not in self.drawn_ticks:
                        mapped_val = self.transform(x)

                        if self.inverted:
                            mapped_val = 1.0 - mapped_val

                        if abs(mapped_val - 1.0) < 0.00001:
                            continue

                        if -0.00001 <= mapped_val <= 1.00001:
                            angle_deg = 90.0 - (mapped_val * 360.0)
                            angle_rad = math.radians(angle_deg)

                            x0 = center_x + radius * math.cos(angle_rad)
                            y0 = center_y + radius * math.sin(angle_rad)

                            r1 = radius + (height * y_mult)
                            x1 = center_x + r1 * math.cos(angle_rad)
                            y1 = center_y + r1 * math.sin(angle_rad)

                            msp.add_line((x0, y0), (x1, y1), dxfattribs=self._dxfattribs())

                            if height == 8.0:
                                label_text = f"{x_rounded:g}"
                                text_radius = radius + ((height + 1.5) * y_mult)
                                tx = center_x + text_radius * math.cos(angle_rad)
                                ty = center_y + text_radius * math.sin(angle_rad)
                                text_rot = angle_deg - 90
                                msp.add_text(label_text, dxfattribs=self._dxfattribs({'height': 2.5, 'rotation': text_rot})).set_placement(
                                    (tx, ty), align=TextEntityAlignment.MIDDLE_CENTER
                                )

                            self.drawn_ticks.add(x_rounded)


# ==========================================
# Scale definitions
# ==========================================

class ScaleC(SlideRuleScale):
    """C scale: log, 1–10, full density."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.sections = [
            {'start': 1.0,  'end': 2.0,  'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0), (0.005, 3.0)]},
            {'start': 2.0,  'end': 4.0,  'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 4.0,  'end': 6.0,  'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.02, 4.0)]},
            {'start': 6.0,  'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.02, 4.0)]},
        ]
    def transform(self, x): return math.log10(x)

class ScaleD(ScaleC):
    """D scale: identical to C, on stator."""
    pass

class ScaleCF(SlideRuleScale):
    """CF scale: C folded at π. Range 1–10 but mapped via log10(x/π)+log10(π)."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.name = "CF"
        # Ticks cover 1–10 same density as C, but transform folds at π
        self.sections = [
            # π ≈ 3.14159  — left segment: π..10
            {'start': math.pi,      'end': 4.0,  'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 4.0,          'end': 6.0,  'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.02, 4.0)]},
            {'start': 6.0,          'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.02, 4.0)]},
            # right segment: 1..π  (wraps around)
            {'start': 1.0,          'end': 2.0,  'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0), (0.005, 3.0)]},
            {'start': 2.0,          'end': math.pi, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
        ]
    def transform(self, x):
        # Fold at π: shift log scale so π maps to 0
        raw = math.log10(x) - math.log10(math.pi)
        return raw % 1.0  # wrap to [0, 1)

class ScaleA(SlideRuleScale):
    """A scale: log, two decades 1–100."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.sections = [
            {'start': 1.0,   'end': 2.0,   'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 2.0,   'end': 5.0,   'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.02, 4.0)]},
            {'start': 5.0,   'end': 10.0,  'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0)]},
            {'start': 10.0,  'end': 20.0,  'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.5, 5.0), (0.1, 4.0)]},
            {'start': 20.0,  'end': 50.0,  'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.5, 5.0), (0.2, 4.0)]},
            {'start': 50.0,  'end': 100.0, 'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.5, 5.0)]},
        ]
    def transform(self, x): return 0.5 * math.log10(x)

class ScaleB(ScaleA):
    """B scale: identical to A, on slide."""
    pass

class ScaleK(SlideRuleScale):
    """K scale: three decades 1–1000."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.sections = [
            {'start': 1.0,    'end': 2.0,    'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 2.0,    'end': 5.0,    'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.02, 4.0)]},
            {'start': 5.0,    'end': 10.0,   'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0)]},
            {'start': 10.0,   'end': 20.0,   'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.5, 5.0), (0.1, 4.0)]},
            {'start': 20.0,   'end': 50.0,   'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.5, 5.0), (0.2, 4.0)]},
            {'start': 50.0,   'end': 100.0,  'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.5, 5.0)]},
            {'start': 100.0,  'end': 200.0,  'ticks': [(100.0, 8.0), (50.0, 7.0), (10.0, 6.0), (5.0, 5.0), (1.0, 4.0)]},
            {'start': 200.0,  'end': 500.0,  'ticks': [(100.0, 8.0), (50.0, 7.0), (10.0, 6.0), (5.0, 5.0), (2.0, 4.0)]},
            {'start': 500.0,  'end': 1000.0, 'ticks': [(100.0, 8.0), (50.0, 7.0), (10.0, 6.0), (5.0, 5.0)]},
        ]
    def transform(self, x): return (1.0 / 3.0) * math.log10(x)

class ScaleS(SlideRuleScale):
    """S scale: log-sin, 5.7°–90°."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.sections = [
            {'start': 5.7,  'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.05, 4.0)]},
            {'start': 10.0, 'end': 20.0, 'ticks': [(5.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.1, 4.0)]},
            {'start': 20.0, 'end': 30.0, 'ticks': [(5.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.2, 4.0)]},
            {'start': 30.0, 'end': 60.0, 'ticks': [(10.0, 8.0), (5.0, 6.0), (1.0, 5.0), (0.5, 4.0)]},
            {'start': 60.0, 'end': 90.0, 'ticks': [(10.0, 8.0), (5.0, 6.0), (1.0, 4.0)]},
        ]
    def transform(self, x): return math.log10(math.sin(math.radians(x))) + 1.0

class ScaleT(SlideRuleScale):
    """T scale: log-tan, 5.7°–45°."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.sections = [
            {'start': 5.7,  'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.05, 4.0)]},
            {'start': 10.0, 'end': 20.0, 'ticks': [(5.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.1, 4.0)]},
            {'start': 20.0, 'end': 30.0, 'ticks': [(5.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.2, 4.0)]},
            {'start': 30.0, 'end': 45.0, 'ticks': [(5.0, 8.0), (1.0, 6.0), (0.5, 5.0)]},
        ]
    def transform(self, x): return math.log10(math.tan(math.radians(x))) + 1.0

class ScaleST(SlideRuleScale):
    """ST scale: log-sin/tan for small angles, 0.5°–6°."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.sections = [
            {'start': 0.5, 'end': 1.0, 'ticks': [(0.1, 8.0), (0.05, 6.0), (0.01, 4.0)]},
            {'start': 1.0, 'end': 2.0, 'ticks': [(0.5, 8.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 2.0, 'end': 4.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.05, 4.0)]},
            {'start': 4.0, 'end': 6.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.05, 4.0)]},
        ]
    def transform(self, x): return math.log10(math.sin(math.radians(x))) + 2.0

class ScaleL(SlideRuleScale):
    """L scale: linear 0–1, gives mantissa of log10."""
    def __init__(self, direction='up', inverted=False, layer=None):
        super().__init__(direction, inverted, layer)
        self.sections = [
            {'start': 0.0,  'end': 0.5,  'ticks': [(0.1, 8.0), (0.05, 6.0), (0.01, 5.0), (0.005, 3.0)]},
            {'start': 0.5,  'end': 1.0,  'ticks': [(0.1, 8.0), (0.05, 6.0), (0.01, 5.0), (0.005, 3.0)]},
        ]
    def transform(self, x): return x  # linear


# ==========================================
# DXF Setup
# ==========================================
doc = ezdxf.new(dxfversion='R2010')
msp = doc.modelspace()

# Create layers with distinct colors
doc.layers.add(LAYER_SLIDE,  dxfattribs={'color': 5})   # blue  — slide: B, CI, C, CF
doc.layers.add(LAYER_STATOR, dxfattribs={'color': 3})   # green — stator: A, D, S, ST, T, K, L

# ==========================================
# Circular layout — radius arrangement
#
# Paired scales share the SAME base circle; ticks point in opposite
# directions so they read back-to-back, exactly like a real slide rule:
#
#   A (ticks outward / 'up')   ──┐  shared circle R_AB
#   B (ticks inward  / 'down') ──┘
#
#   C (ticks outward / 'up')   ──┐  shared circle R_CD
#   D (ticks inward  / 'down') ──┘
#
# Full layout outer → inner:
#   K        (stator, ticks outward)
#   A / B    (stator A outward, slide B inward)   ← paired
#   CF       (slide, ticks outward)
#   CI       (slide, ticks inward — inverted C)
#   C / D    (slide C outward, stator D inward)   ← paired
#   S        (stator, ticks inward)
#   ST       (stator, ticks inward)
#   T        (stator, ticks inward)
#   L        (stator, ticks inward, innermost)
#
# GAP between independent circles = 20 mm  (tick field ≤ 12 mm + 8 mm margin)
# Paired circles are separated by only 1 mm so they share a nearly-coincident
# baseline — visually they appear as a single ruled edge.
# ==========================================

CENTER = (0.0, 0.0)
GAP   = 20.0   # mm between independent scale circles
PAIR  =  1.0   # mm offset between the two circles of a mated pair
               # (non-zero so DXF viewers don't merge the lines)

R_K   = 230.0
R_AB  = R_K  - GAP          # 210  — shared baseline for A (up) and B (down)
R_CF  = R_AB - GAP          # 190
R_CI  = R_CF - GAP          # 170
R_CD  = R_CI - GAP          # 150  — shared baseline for C (up) and D (down)
R_S   = R_CD - GAP          # 130
R_ST  = R_S  - GAP          # 110
R_T   = R_ST - GAP          # 90
R_L   = R_T  - GAP          # 70

# A sits just outside the shared circle (ticks go further outward)
# B sits just inside it (ticks go inward)
R_A   = R_AB + PAIR         # 211
R_B   = R_AB - PAIR         # 209

# C sits just outside the shared circle (ticks go outward)
# D sits just inside it (ticks go inward)
R_C   = R_CD + PAIR         # 151
R_D   = R_CD - PAIR         # 149

# Each scale object paired with its explicit draw radius
scale_draw_pairs = [
    # (scale_object,                                          radius)
    (ScaleK (direction='up',               layer=LAYER_STATOR), R_K),
    # A/B pair — A outward (stator), B inward (slide)
    (ScaleA (direction='up',               layer=LAYER_STATOR), R_A),
    (ScaleB (direction='down',             layer=LAYER_SLIDE),  R_B),
    # CF and CI on the slide
    (ScaleCF(direction='up',               layer=LAYER_SLIDE),  R_CF),
    (ScaleC (direction='up', inverted=True, layer=LAYER_SLIDE), R_CI),   # CI
    # C/D pair — C outward (slide), D inward (stator)
    (ScaleC (direction='up',               layer=LAYER_SLIDE),  R_C),
    (ScaleD (direction='down',             layer=LAYER_STATOR), R_D),
    # Inner stator trig / log scales
    (ScaleS (direction='down',             layer=LAYER_STATOR), R_S),
    (ScaleST(direction='down',             layer=LAYER_STATOR), R_ST),
    (ScaleT (direction='down',             layer=LAYER_STATOR), R_T),
    (ScaleL (direction='down',             layer=LAYER_STATOR), R_L),
]

for scale_obj, r in scale_draw_pairs:
    scale_obj.draw_circular(msp, radius=r, center_x=CENTER[0], center_y=CENTER[1])

doc.saveas("requested_scales.dxf")
print("Successfully generated requested_scales.dxf!")
print(f"Layers: '{LAYER_SLIDE}' (blue)  |  '{LAYER_STATOR}' (green)")
print("Paired baselines:  A/B share R≈210,  C/D share R≈150")
print(f"All radii (mm): K={R_K}, A={R_A}, B={R_B}, CF={R_CF}, CI={R_CI}, "
      f"C={R_C}, D={R_D}, S={R_S}, ST={R_ST}, T={R_T}, L={R_L}")
