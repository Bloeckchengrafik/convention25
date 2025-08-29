import abc
from dataclasses import dataclass

from svgpathtools.path import transform_segments_together

from .emergency_trap import EmergencyStop
from .sizing import Distance
from swarm import FtSwarmStepper

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
        await printer.move_to(self.x, self.y)

@dataclass
class SwitchTool(Command):
    tool_id: int

    async def execute(self, printer: 'Printer'):
        pass

class Printer:
    def __init__(self, x_axis: FtSwarmStepper, y_axis: FtSwarmStepper, es: EmergencyStop) -> None:
        self.x_axis = x_axis
        self.y_axis = y_axis
        self.es = es
        self.step_x = 0
        self.step_y = 0
        self.speed = 1000

    async def home(self):
        await self.x_axis.set_homing_offset(1000)
        await self.x_axis.set_homing_offset(-1000)
        await self.x_axis.homing_and_wait(-500000)
        self.es.trap()
        await self.y_axis.homing_and_wait(500000)
        self.es.trap()

        await self.y_axis.set_distance(-(Distance(cm=11, mm=5).to_steps(1)), True)
        await self.y_axis.run_and_wait()
        self.es.trap()

        await self.x_axis.set_distance(Distance(cm=7, mm=5).to_steps(1), True)
        await self.x_axis.run_and_wait()
        self.es.trap()

    async def move_to(self, x: Distance, y: Distance):
        target_x = x.to_steps(1)
        target_y = y.to_steps(1)

        dx = target_x - self.step_x
        dy = target_y - self.step_y

        self.step_x = target_x
        self.step_y = target_y

        await self.x_axis.set_speed(self.speed)
        await self.y_axis.set_speed(self.speed)

        await self.x_axis.set_distance(dx, True)
        await self.y_axis.set_distance(dy, True)
        await self.x_axis.run()
        await self.y_axis.run()
        await self.x_axis.wait_done()
        await self.y_axis.wait_done()
