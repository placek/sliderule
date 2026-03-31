#!/usr/bin/env nix-shell
#!nix-shell -i python3 -p python3 python3Packages.ezdxf

import ezdxf
import math
from ezdxf.enums import TextEntityAlignment

RULE_LENGTH = 250.0

class SlideRuleScale:
    """Base class for all slide rule scales."""
    def __init__(self, direction='up', inverted=False):
        self.sections = []
        self.drawn_ticks = set()
        self.direction = direction 
        self.inverted = inverted
        self.name = self.__class__.__name__.replace("Scale", "")
        if self.inverted and not self.name.endswith('I'):
            self.name += "I"

    def transform(self, x):
        raise NotImplementedError

    def draw(self, msp, y_offset=0.0):
        y_mult = 1.0 if self.direction == 'up' else -1.0
        text_align = TextEntityAlignment.BOTTOM_CENTER if self.direction == 'up' else TextEntityAlignment.TOP_CENTER
        msp.add_text(self.name, dxfattribs={'height': 3.0}).set_placement(
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
                        # Apply the inversion mapping
                        if self.inverted:
                            mapped_val = 1.0 - mapped_val
                        # To handle minor floating point drift precisely around 0.0 and 1.0 bounds
                        if -0.00001 <= mapped_val <= 1.00001:
                            pos_x = mapped_val * RULE_LENGTH
                            msp.add_line((pos_x, y_offset), (pos_x, y_offset + (height * y_mult)))
                            if height == 8.0:
                                label_text = f"{x_rounded:g}" 
                                msp.add_text(label_text, dxfattribs={'height': 2.5}).set_placement(
                                    (pos_x, y_offset + ((height + 0.5) * y_mult)), 
                                    align=text_align
                                )
                            self.drawn_ticks.add(x_rounded)

        msp.add_line((0, y_offset), (RULE_LENGTH, y_offset))


class ScaleC(SlideRuleScale):
    def __init__(self, direction='up', inverted=False):
        super().__init__(direction, inverted)
        self.sections = [
            {'start': 1.0, 'end': 2.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0), (0.005, 3.0)]},
            {'start': 2.0, 'end': 3.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 3.0, 'end': 6.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.02, 5.0)]},
            {'start': 6.0, 'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0)]}
        ]
    def transform(self, x): return math.log10(x)

class ScaleD(ScaleC): pass

class ScaleA(SlideRuleScale):
    def __init__(self, direction='up', inverted=False):
        super().__init__(direction, inverted)
        self.sections = [
            {'start': 1.0, 'end': 2.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 2.0, 'end': 5.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.02, 4.0)]},
            {'start': 5.0, 'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 5.0), (0.05, 4.0)]},
            {'start': 10.0, 'end': 20.0, 'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.5, 5.0), (0.1, 4.0)]},
            {'start': 20.0, 'end': 50.0, 'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.2, 4.0)]},
            {'start': 50.0, 'end': 100.0, 'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 5.0), (0.5, 4.0)]}
        ]
    def transform(self, x): return 0.5 * math.log10(x)

class ScaleB(ScaleA): pass

class ScaleK(SlideRuleScale):
    def __init__(self, direction='up', inverted=False):
        super().__init__(direction, inverted)
        self.sections = [
            {'start': 1.0, 'end': 3.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 6.0), (0.02, 4.0)]},
            {'start': 3.0, 'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 7.0), (0.1, 5.0), (0.05, 4.0)]},
            {'start': 10.0, 'end': 30.0, 'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 6.0), (0.2, 4.0)]},
            {'start': 30.0, 'end': 100.0, 'ticks': [(10.0, 8.0), (5.0, 7.0), (1.0, 5.0), (0.5, 4.0)]},
            {'start': 100.0, 'end': 300.0, 'ticks': [(100.0, 8.0), (50.0, 7.0), (10.0, 6.0), (2.0, 4.0)]},
            {'start': 300.0, 'end': 1000.0, 'ticks': [(100.0, 8.0), (50.0, 7.0), (10.0, 5.0), (5.0, 4.0)]}
        ]
    def transform(self, x): return (1.0 / 3.0) * math.log10(x)

class ScaleS(SlideRuleScale):
    def __init__(self, direction='up', inverted=False):
        super().__init__(direction, inverted)
        self.sections = [
            {'start': 5.8, 'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.05, 4.0)]},
            {'start': 10.0, 'end': 20.0, 'ticks': [(10.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.1, 4.0)]},
            {'start': 20.0, 'end': 30.0, 'ticks': [(10.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.2, 4.0)]},
            {'start': 30.0, 'end': 60.0, 'ticks': [(10.0, 8.0), (5.0, 6.0), (1.0, 5.0), (0.5, 4.0)]},
            {'start': 60.0, 'end': 90.0, 'ticks': [(10.0, 8.0), (5.0, 6.0), (1.0, 4.0)]} 
        ]
    def transform(self, x): return math.log10(math.sin(math.radians(x))) + 1.0

class ScaleT(SlideRuleScale):
    def __init__(self, direction='up', inverted=False):
        super().__init__(direction, inverted)
        self.sections = [
            {'start': 5.8, 'end': 10.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.05, 4.0)]},
            {'start': 10.0, 'end': 20.0, 'ticks': [(10.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.1, 4.0)]},
            {'start': 20.0, 'end': 30.0, 'ticks': [(10.0, 8.0), (1.0, 6.0), (0.5, 5.0), (0.2, 4.0)]},
            {'start': 30.0, 'end': 45.0, 'ticks': [(10.0, 8.0), (5.0, 6.0), (1.0, 5.0), (0.5, 4.0)]}
        ]
    def transform(self, x): return math.log10(math.tan(math.radians(x))) + 1.0

class ScaleST(SlideRuleScale):
    def __init__(self, direction='up', inverted=False):
        super().__init__(direction, inverted)
        self.sections = [
            {'start': 0.5, 'end': 1.0, 'ticks': [(0.1, 8.0), (0.05, 6.0), (0.01, 5.0), (0.005, 3.0)]},
            {'start': 1.0, 'end': 2.0, 'ticks': [(1.0, 8.0), (0.1, 6.0), (0.05, 5.0), (0.01, 4.0)]},
            {'start': 2.0, 'end': 4.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.02, 4.0)]},
            {'start': 4.0, 'end': 6.0, 'ticks': [(1.0, 8.0), (0.5, 6.0), (0.1, 5.0), (0.05, 4.0)]}
        ]
    def transform(self, x): return math.log10(math.sin(math.radians(x))) + 2.0


# ==========================================
# Execution / DXF Generation
# ==========================================
doc = ezdxf.new(dxfversion='R2010')
msp = doc.modelspace()

# Added the CI and DI scales to the layout as a demonstration.
scales = {
    'K':  ScaleK(direction='up'),
    'A':  ScaleA(direction='down'),
    'B':  ScaleB(direction='up'),
    'CI': ScaleC(direction='down', inverted=True), # Inverted scale
    'C':  ScaleC(direction='down'),
    'D':  ScaleD(direction='up'),
    'DI': ScaleD(direction='down', inverted=True)  # Inverted scale
}

current_y_offset = 0.0
SPACING = 20.0

for name, scale_obj in scales.items():
    scale_obj.draw(msp, y_offset=current_y_offset)
    current_y_offset += SPACING

doc.saveas("output.dxf")
