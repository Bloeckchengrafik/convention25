from ...printer import Command
from . import colinear_opt, sort_tool_opt, sort_path_opt
import functools

def optimize(commands: list[Command]) -> list[Command]:
    opts = [
        colinear_opt.optimize_colinear,
        sort_tool_opt.optimize_sort_tool,
        sort_path_opt.optimize_sort_path
    ]
    return functools.reduce(lambda cmds, opt: opt(cmds), opts, commands)
