import asyncio
import logging
from swarm import FtSwarm
from swarm.swarm import FtSwarmIO

class FtSwarmStepper(FtSwarmIO):
    def __init__(self, swarm, port_name) -> None:
        super().__init__(swarm, port_name)

    async def post_init(self) -> None:
        pass

    async def homing(self, max_steps: int):
        await self._swarm.send(self._port_name, "homing", max_steps)

    async def set_distance(self, distance: int, relative: bool):
        await self._swarm.send(self._port_name, "setDistance", distance, int(relative))

    async def run(self):
        await self._swarm.send(self._port_name, "run")

    async def stop(self):
        await self._swarm.send(self._port_name, "stop")

    async def is_running(self) -> bool:
        return await self._swarm.send(self._port_name, "isRunning") == 1


async def read_button():
    swarm = FtSwarm("/dev/ttyUSB0")
    swarm.logger.setLevel(logging.DEBUG)
    await swarm.send("ftSwarm400", "setMicrostepMode", 2)
    stepper = await swarm._get_object("Stepper1", FtSwarmStepper)

    await stepper.homing(500000)
    input("press enter to continue")
    await stepper.stop()

    await stepper.set_distance(-10000, False)
    await stepper.run()
    input("press enter to stop")
    await stepper.stop()

asyncio.run(read_button())
