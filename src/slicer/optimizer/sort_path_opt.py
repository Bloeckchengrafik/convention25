from dataclasses import dataclass
from typing import List, Tuple
from ...printer import Command, ExtrudeTo, MoveTo, SwitchTool
import numpy as np

@dataclass
class PathSegment:
    """Represents a continuous segment of commands for a single toolpath."""
    commands: list[Command]
    start_point: complex
    end_point: complex

def get_point(cmd: Command) -> complex | None:
    """Helper function to get the point from a command."""
    if isinstance(cmd, (MoveTo, ExtrudeTo)):
        return complex(cmd.x.mm, cmd.y.mm)
    return None

def calculate_distance(p1: complex, p2: complex) -> float:
    """Calculates the Euclidean distance between two complex points."""
    return np.sqrt((p1.real - p2.real)**2 + (p1.imag - p2.imag)**2)

def optimize_sort_path(commands: list[Command]) -> list[Command]:
    """
    Optimizes the order of toolpaths to minimize the total travel distance.

    This function identifies individual paths (segments starting with MoveTo or SwitchTool),
    sorts them using a greedy algorithm to minimize travel, and then
    reconstructs the command list.

    Args:
        commands: The original list of Command objects.

    Returns:
        A new list of Command objects with optimized path order.
    """
    if not commands:
        return []

    # 1. Split the command list into individual path segments
    paths: List[PathSegment] = []
    current_segment: list[Command] = []

    for cmd in commands:
        if isinstance(cmd, (SwitchTool, MoveTo)):
            if current_segment:
                # A path has just finished, so store it.
                segment_start_point = get_point(next((c for c in current_segment if isinstance(c, MoveTo)), None))
                segment_end_point = get_point(current_segment[-1])

                # Only add valid path segments (those with a start and end point)
                if segment_start_point is not None and segment_end_point is not None:
                    paths.append(PathSegment(
                        commands=current_segment,
                        start_point=segment_start_point,
                        end_point=segment_end_point
                    ))

            # Start a new segment with the current command.
            current_segment = [cmd]
        else: # ExtrudeTo
            current_segment.append(cmd)

    # Add the last segment after the loop.
    if current_segment:
        segment_start_point = get_point(next((c for c in current_segment if isinstance(c, MoveTo)), None))
        segment_end_point = get_point(current_segment[-1])
        if segment_start_point is not None and segment_end_point is not None:
            paths.append(PathSegment(
                commands=current_segment,
                start_point=segment_start_point,
                end_point=segment_end_point
            ))

    # 2. Sort paths using a greedy algorithm
    optimized_paths: List[PathSegment] = []
    # Use a list instead of a set to avoid TypeError, and use pop for efficiency
    unvisited_paths: List[PathSegment] = paths.copy()

    if not unvisited_paths:
        return []

    # Start with the first path in the original list
    current_path = unvisited_paths.pop(0)
    optimized_paths.append(current_path)

    while unvisited_paths:
        last_point = optimized_paths[-1].end_point
        closest_path_index = -1
        min_distance = float('inf')

        for i, path in enumerate(unvisited_paths):
            distance_to_start = calculate_distance(last_point, path.start_point)

            if distance_to_start < min_distance:
                min_distance = distance_to_start
                closest_path_index = i

        if closest_path_index != -1:
            closest_path = unvisited_paths.pop(closest_path_index)
            optimized_paths.append(closest_path)
        else:
            break

    # 3. Reconstruct the command list with optimized paths
    optimized_commands: list[Command] = []
    for path in optimized_paths:
        optimized_commands.extend(path.commands)

    return optimized_commands
