import abc
from dataclasses import dataclass
import math

from svgpathtools.path import transform_segments_together

from src.config import Configuration
from src.io import Io

from .emergency_trap import EmergencyStop
from .sizing import Distance
from swarm import FtSwarm, FtSwarmStepper, MicrostepMode

class Command(abc.ABC):
    @abc.abstractmethod
    async def execute(self, printer: 'Printer'):
        pass

@dataclass
class MoveTo(Command):
    x: Distance
    y: Distance

    async def execute(self, printer: 'Printer'):
        await printer.move_to(self.x, self.y)

@dataclass
class ExtrudeTo(Command):
    x: Distance
    y: Distance

    async def execute(self, printer: 'Printer'):
        printer.should_extrude = True
        await printer.move_to(self.x, self.y)

@dataclass
class SwitchTool(Command):
    tool_id: int

    async def execute(self, printer: 'Printer'):
        printer.tool = self.tool_id

class Printer:
    def __init__(self, swarm: FtSwarm, x_axis: FtSwarmStepper, y_axis: FtSwarmStepper, tools: list[FtSwarmStepper], config: Configuration, es: EmergencyStop) -> None:
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.es = es
        self.step_x = 0
        self.step_y = 0
        self.speed = 4000
        self.swarm = swarm
        self.tools = tools
        self.tool = 0
        self.should_extrude = False
        self.config = config

    async def home(self, do_finalize = True):
        await self.swarm.set_microstep_mode(Io.PRIMARY_PWRDRIVE, MicrostepMode.FULL)
        await self.y_axis.set_speed(3000)
        await self.x_axis.set_speed(7000)
        await self.y_axis.set_homing_offset(500)
        await self.x_axis.set_homing_offset(-500)
        await self.x_axis.homing_and_wait(-500000)
        self.es.trap()
        await self.y_axis.homing_and_wait(500000)
        self.es.trap()

        await self.swarm.set_microstep_mode(Io.PRIMARY_PWRDRIVE, MicrostepMode.HALF)
        if not do_finalize:
            return
        await self.y_axis.set_distance(-(Distance(cm=11, mm=0).to_steps(1)), True)
        await self.y_axis.run_and_wait()
        self.es.trap()

        await self.x_axis.set_distance(Distance(cm=7, mm=0).to_steps(1), True)
        await self.x_axis.run_and_wait()
        self.es.trap()

    async def move_to(self, x: Distance, y: Distance):
        target_x = -x.to_steps(1)
        target_y = y.to_steps(1)

        dx = target_x - self.step_x
        dy = target_y - self.step_y

        self.step_x = target_x
        self.step_y = target_y

        distance = math.sqrt(dx**2 + dy**2)
        if distance == 0: return
        angle_rad = math.atan2(dy, dx)
        vx = self.speed * math.cos(angle_rad)
        vy = self.speed * math.sin(angle_rad)

        should_extrude = self.should_extrude
        tool: FtSwarmStepper = None # type: ignore
        if should_extrude:
            self.should_extrude = False
            tool = self.tools[self.tool]
            steps = int(abs(distance) * self.config.flow_rate * -1)
            time_x = abs(dx) / abs(vx) if vx != 0 else 0
            time_y = abs(dy) / abs(vy) if vy != 0 else 0
            movement_time = max(time_x, time_y)
            tool_speed = int(steps / movement_time) if movement_time > 0 else 0
            await tool.set_speed(tool_speed)
            await tool.set_distance(steps, True)

        await self.x_axis.set_speed(abs(int(vx)))
        await self.y_axis.set_speed(abs(int(vy)))

        print(f"MoveTo: {dx}/{abs(int(vx))} {dy}/{abs(int(vy))} {should_extrude}")

        if dx != 0:
            await self.x_axis.set_distance(dx, True)
        if dy != 0:
            await self.y_axis.set_distance(dy, True)
        if dx != 0:
            await self.x_axis.run()
        if dy != 0:
            await self.y_axis.run()
        if should_extrude:
            await tool.run()
        if dx != 0:
            await self.x_axis.wait_done()
        if dy != 0:
            await self.y_axis.wait_done()
        if should_extrude:
            await tool.wait_done()
