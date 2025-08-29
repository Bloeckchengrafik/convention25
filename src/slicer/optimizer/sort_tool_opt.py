import abc
from collections import defaultdict
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
from matplotlib.lines import Line2D

from svgpathtools.paths2svg import Line
from svgpathtools import svg2paths
from ...printer import Command, SwitchTool

def optimize_sort_tool(commands: list[Command]) -> list[Command]:
    """
    Optimizes a list of commands by sorting paths by tool and
    removing redundant SwitchTool commands.

    This function first groups all commands by their associated tool ID.
    It then reconstructs a new list of commands, starting each tool's
    segment with a single SwitchTool command, thus minimizing tool changes.

    Args:
        commands: A list of Command objects, potentially with
                  interspersed SwitchTool commands.

    Returns:
        A new list of Command objects sorted by tool, with optimized tool changes.
    """
    # Group commands by tool ID
    tool_commands = defaultdict(list)
    current_tool_id = None

    for cmd in commands:
        if isinstance(cmd, SwitchTool):
            current_tool_id = cmd.tool_id
        elif current_tool_id is not None:
            tool_commands[current_tool_id].append(cmd)

    # Reconstruct the optimized command list
    optimized_commands = []
    sorted_tool_ids = sorted(tool_commands.keys())

    for tool_id in sorted_tool_ids:
        # Add a SwitchTool command for each tool group
        optimized_commands.append(SwitchTool(tool_id))
        # Add all the MoveTo and ExtrudeTo commands for this tool
        optimized_commands.extend(tool_commands[tool_id])

    return optimized_commands
