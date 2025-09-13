import asyncio
from asyncio.tasks import Task

from numpy import sign
from src.emergency_trap import EmergencyStop
from src.util import Aobject
from src.io import Io
from swarm import FtSwarm, MicrostepMode
from swarm.swarm import FtSwarmStepper

class Rotator(Aobject):
    async def __init__(self, swarm: FtSwarm):
        await super().__init__()
        self.swarm = swarm
        self.pusher = await swarm.get_motor(Io.PUSHER_MOTOR)
        self.rotator_es_printstage = await swarm.get_switch(Io.ROTATOR_ES_PRINTSTAGE)
        self.rotator_es_storage = await swarm.get_switch(Io.ROTATOR_ES_STORAGE)
        self.rotator = await swarm.get_motor(Io.ROTATOR_MOTOR)

    async def home_pusher(self):
        await self.pusher.set_speed(-4095)
        await asyncio.sleep(10)
        await self.pusher.set_speed(0)

    async def rotate_to_printstage(self):
        await self.rotator.set_speed(-2000)
        while await self.rotator_es_printstage.is_released():
            await asyncio.sleep(0.1)
        await self.rotator.set_speed(0)

    async def rotate_to_storage(self):
        await self.rotator.set_speed(2000)
        while await self.rotator_es_storage.is_released():
            await asyncio.sleep(0.1)
        await self.rotator.set_speed(0)

    async def home(self):
        await asyncio.gather(
            self.home_pusher(),
            self.rotate_to_printstage()
        )

    async def push(self):
        await self.pusher.set_speed(4000)
        await asyncio.sleep(1)
        await self.pusher.set_speed(0)

    async def action(self):
        await self.push()
        await asyncio.gather(
            self.home_pusher(),
            self.rotate_to_storage()
        )

class XAxis(Aobject):
    async def __init__(self, swarm: FtSwarm) -> None:
        await super().__init__()
        self.x_axis = await swarm.get_motor(Io.STORAGE_X)
        self.x_reed = await swarm.get_reed_switch(Io.STORAGE_X_REED)
        self.x_endstop = await swarm.get_switch(Io.STORAGE_X_ES)

    async def home(self):
        await self.x_axis.set_speed(-4000)
        while await self.x_endstop.is_released():
            await asyncio.sleep(0.1)
        await self.x_axis.set_speed(0)

    async def next(self):
        flag = await self.x_reed.is_pressed()
        is_on = False
        await self.x_axis.set_speed(4000)
        while flag or (not is_on):
            is_on = await self.x_reed.is_pressed()
            flag = flag and is_on
            await asyncio.sleep(0.1)
        await self.x_axis.set_speed(0)

class YAxis(Aobject):
    POSITION_BOTTOM_PICKUP = 100
    POSITION_SEGMENT_RIGHT = 2100
    POSITION_SEGMENT_LEFT = 3100

    async def __init__(self, swarm: FtSwarm) -> None:
        await super().__init__()
        self.y_axis = await swarm.get_motor(Io.STORAGE_Y)
        self.y_endstop = await swarm.get_switch(Io.STORAGE_Y_ES)
        self.rotary = await swarm.get_rotary(Io.STORAGE_Y_KNOB)
        self.current_position = 0

    async def home(self):
        await self.y_axis.set_speed(4000)
        while not await self.y_endstop.is_pressed():
            await asyncio.sleep(0.01)
        await self.y_axis.set_speed(0)
        await self.rotary.set_home()
        self.current_position = 0

    async def goto(self, position: int):
        delta = position - self.current_position
        await self.y_axis.set_speed(sign(delta) * -4000)
        await self.rotary.set_home()
        while await self.rotary.get_value() < abs(delta):
            await asyncio.sleep(0.1)
        await self.y_axis.set_speed(0)
        self.current_position = position


class Storage(Aobject):
    async def __init__(self, swarm: FtSwarm, y_axis: FtSwarmStepper, es: EmergencyStop) -> None:
        await super().__init__()
        self.printer_y_axis = y_axis
        self.rotator = await Rotator(swarm)
        self.swarm = swarm
        self.es = es
        self.storage_x_axis = await XAxis(swarm)
        self.storage_y_axis = await YAxis(swarm)

    async def home_print_to_storage(self):
        await self.swarm.set_microstep_mode(Io.PRIMARY_PWRDRIVE, MicrostepMode.FULL)
        await self.printer_y_axis.set_speed(3000)
        await self.printer_y_axis.set_homing_offset(-200)
        await self.printer_y_axis.homing_and_wait(-500000)
        self.es.trap()

        await self.swarm.set_microstep_mode(Io.PRIMARY_PWRDRIVE, MicrostepMode.HALF)

    async def home_claw(self):
        await self.storage_x_axis.home()
        await self.storage_x_axis.next()
        await self.storage_y_axis.home()
        await self.storage_x_axis.home()

    async def dumb_output(self):
        await self.storage_y_axis.goto(YAxis.POSITION_SEGMENT_RIGHT)
        asyncio.create_task(self.rotator.rotate_to_printstage())
        await self.storage_x_axis.next()
        await self.storage_x_axis.next()
        await self.storage_y_axis.goto(YAxis.POSITION_SEGMENT_LEFT)
        await self.storage_x_axis.home()
        await self.storage_x_axis.next()
        await self.storage_y_axis.goto(YAxis.POSITION_SEGMENT_RIGHT)

    async def from_printer_to_storage(self) -> asyncio.Task:
        await asyncio.gather(
            self.rotator.home(),
            self.home_print_to_storage(),
            self.home_claw()
        )
        print("Home completed")
        await self.rotator.action()
        print("Rotator action completed")
        return asyncio.create_task(self.dumb_output())
