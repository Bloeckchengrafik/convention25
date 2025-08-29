import abc
from collections import defaultdict
from dataclasses import dataclass, field
import matplotlib.pyplot as plt
from matplotlib.patches import Circle
import numpy as np
from matplotlib.lines import Line2D

from svgpathtools.paths2svg import Line
from svgpathtools import svg2paths

from .printer import Command, ExtrudeTo, MoveTo, SwitchTool
from .sizing import Distance

def is_collinear(p1: complex, p2: complex, p3: complex) -> bool:
    """
    Checks if three points are collinear.
    This function uses the cross-product method to determine collinearity.
    """
    # Use a small tolerance for floating-point comparisons
    tolerance = 1e-6
    return abs((p2.imag - p1.imag) * (p3.real - p2.real) - (p2.real - p1.real) * (p3.imag - p2.imag)) < tolerance

def optimize_colinear(commands: list[Command]) -> list[Command]:
    """
    Optimizes a list of commands by removing redundant extrude commands.
    This function combines consecutive collinear ExtrudeTo commands into a single
    command, resulting in a more efficient and cleaner toolpath.

    Args:
        commands: A list of Command objects.

    Returns:
        A new list of optimized Command objects.
    """
    if not commands:
        return []

    optimized_commands: list[Command] = [commands[0]]
    current_x, current_y = 0, 0

    # Get the initial position from the first command if it's a MoveTo
    if isinstance(commands[0], MoveTo):
        current_x = commands[0].x.mm
        current_y = commands[0].y.mm

    # Track the start of the current extrude segment
    extrude_start_x = current_x
    extrude_start_y = current_y
    is_extruding = False

    for i in range(1, len(commands)):
        current_cmd = commands[i]

        if isinstance(current_cmd, ExtrudeTo):
            if not is_extruding:
                # Start of a new extrude segment
                extrude_start_x = current_x
                extrude_start_y = current_y
                is_extruding = True

            last_cmd_optimized = optimized_commands[-1]

            if isinstance(last_cmd_optimized, ExtrudeTo):
                # We have at least two consecutive ExtrudeTo commands.
                # Check for collinearity.
                p1 = complex(extrude_start_x, extrude_start_y)
                p2 = complex(last_cmd_optimized.x.mm, last_cmd_optimized.y.mm)
                p3 = complex(current_cmd.x.mm, current_cmd.y.mm)

                if is_collinear(p1, p2, p3):
                    # Points are collinear, so replace the previous extrude command with the new one.
                    # This effectively extends the segment to the new endpoint.
                    optimized_commands[-1] = ExtrudeTo(x=current_cmd.x, y=current_cmd.y)
                else:
                    # Not collinear, so this is a new segment.
                    optimized_commands.append(current_cmd)
                    extrude_start_x = last_cmd_optimized.x.mm
                    extrude_start_y = last_cmd_optimized.y.mm
            else:
                # First ExtrudeTo after a MoveTo or SwitchTool
                optimized_commands.append(current_cmd)
        else:
            is_extruding = False
            optimized_commands.append(current_cmd)
            # Update position for future segments
            if isinstance(current_cmd, MoveTo):
                current_x = current_cmd.x.mm
                current_y = current_cmd.y.mm

            # Reset extrude start point to current position
            extrude_start_x = current_x
            extrude_start_y = current_y

    return optimized_commands

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

def optimize(commands: list[Command]) -> list[Command]:
    return optimize_sort_tool(optimize_colinear(commands))
