import abc
from dataclasses import dataclass, field
from matplotlib.lines import Line2D
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np

from svgpathtools.paths2svg import Line
from svgpathtools import svg2paths

from . import SlicerSettings
from ..printer import Command, ExtrudeTo, MoveTo, SwitchTool
from ..sizing import Distance

def visualize(commands: list[Command], settings: SlicerSettings = SlicerSettings()) -> None:
    """
    Visualize the toolpath commands using matplotlib.
    This function creates a visual representation of the commands, which are
    already shifted by the slicer. The visualization directly plots the
    coordinates given by the commands.

    Args:
        commands: List of Command objects to visualize
        settings: SlicerSettings containing tool definitions and colors
    """
    fig, ax = plt.subplots(figsize=(10, 10))
    ax.set_aspect('equal')
    ax.set_title("Visualization of Slicer Commands")
    ax.grid(True)
    ax.set_xlabel("X (mm)")
    ax.set_ylabel("Y (mm)")

    tool_colors = {tool.id: tool.color for tool in settings.tools}
    current_x, current_y = None, None
    current_tool_id = 0

    for cmd in commands:
        if isinstance(cmd, SwitchTool):
            current_tool_id = cmd.tool_id
            print(f"Switched to tool {current_tool_id} (color: {tool_colors.get(current_tool_id, 'unknown')})")

        elif isinstance(cmd, MoveTo):
            new_x = cmd.x.mm
            new_y = cmd.y.mm

            if current_x is not None and current_y is not None:
                ax.plot([current_x, new_x], [current_y, new_y], color='gray', linestyle='--', linewidth=1, alpha=0.6)

            current_x, current_y = new_x, new_y

        elif isinstance(cmd, ExtrudeTo):
            x_new, y_new = cmd.x.mm, cmd.y.mm
            color = tool_colors.get(current_tool_id, 'black')

            if current_x is not None and current_y is not None:
                ax.plot([current_x, x_new], [current_y, y_new], color=color, linewidth=2)

            ax.add_patch(Circle((x_new, y_new), 0.2, color=color, alpha=0.5))
            current_x, current_y = x_new, y_new

    # Add legend
    legend_handles = []
    for tool in settings.tools:
        legend_handles.append(Line2D([0], [0], color=tool.color, lw=2, label=f"Tool {tool.id} Extrude"))
    legend_handles.append(Line2D([0], [0], color='gray', lw=1, linestyle='--', label="Travel Move"))

    ax.legend(handles=legend_handles)
    plt.show()
