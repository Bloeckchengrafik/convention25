from dataclasses import dataclass
from .sizing import Distance
from svgpathtools import svg2paths

@dataclass
class Tool:
    id: int
    color: str
    xOffset: Distance
    yOffset: Distance


@dataclass
class SlicerSettings:
    tools: list[Tool] = [
        Tool(0, "#ff0000", Distance(mm= 4), Distance(mm=8)), 
        Tool(1, "#0000ff", Distance(mm=15), Distance(mm=8)), 
        Tool(2, "#aaaaaa", Distance(mm=26), Distance(mm=8))
    ]


def slice_to_gcode(filename: str, settings: SlicerSettings = SlicerSettings()) -> str:
    paths, attrs = svg2paths(filename)
    return ""

if __name__ == "__main__":
    gcode = slice_to_gcode("test.svg")
    with open("test.gcode", "w") as f:
        f.write(gcode)
