import abc
from dataclasses import dataclass, field
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

from svgpathtools.paths2svg import Line
from svgpathtools import svg2paths

from ..printer import Command, ExtrudeTo, MoveTo, SwitchTool
from ..sizing import Distance

@dataclass
class Tool:
    id: int
    color: str
    xOffset: Distance
    yOffset: Distance

@dataclass
class SlicerSettings:
    tools: list[Tool] = field(default_factory=lambda: [
        Tool(0, "#ff0000", Distance(mm= 4), Distance(mm=8)),
        Tool(1, "#0000ff", Distance(mm=15), Distance(mm=8)),
        Tool(2, "#aaaaaa", Distance(mm=26), Distance(mm=8))
    ])

def slice(filename: str, settings: SlicerSettings = SlicerSettings()) -> list[Command]:
    """
    Convert an SVG file into a sequence of tool commands.
    This function generates a toolpath with coordinates that are already
    shifted to account for the tool's offset. The SwitchTool command simply
    selects the correct motor.

    Args:
        filename: Path to the SVG file to process
        settings: Configuration settings including tool definitions

    Returns:
        A list of Command objects representing the toolpath
    """
    paths, attrs = svg2paths(filename) # type: ignore
    commands: list[Command] = []
    current_tool_id = None

    for path, attr in zip(paths, attrs):
        tool_index = 0
        if 'stroke' in attr:
            stroke_color = attr['stroke'].lower()
            for i, tool in enumerate(settings.tools):
                if tool.color.lower() == stroke_color:
                    tool_index = i
                    break

        tool = settings.tools[tool_index]

        toolpath_points: list[complex] = []
        if isinstance(path, Line):
            toolpath_points = [path.start, path.end] # type: ignore
        else:
            num = int(path.length()) # type: ignore
            if num < 2: num = 2
            toolpath_points = [path.point(x / (num - 1)) for x in range(num)]

        if not toolpath_points:
            continue

        # If a new path is started or the tool changes, issue a SwitchTool command
        # and a MoveTo command to travel to the start of the new path.
        if current_tool_id != tool.id:
            commands.append(SwitchTool(tool.id))
            current_tool_id = tool.id

        # A MoveTo command should always precede an extruding path to avoid
        # drawing lines between disconnected shapes.
        first_point = toolpath_points[0]
        shifted_first_point = complex(first_point.real + tool.xOffset.mm, first_point.imag + tool.yOffset.mm)
        commands.append(MoveTo(Distance(mm=shifted_first_point.real), Distance(mm=shifted_first_point.imag)))

        # Extrude to all subsequent points.
        for point in toolpath_points[1:]:
            shifted_point = complex(point.real + tool.xOffset.mm, point.imag + tool.yOffset.mm)
            commands.append(ExtrudeTo(Distance(mm=shifted_point.real), Distance(mm=shifted_point.imag)))

    return commands
