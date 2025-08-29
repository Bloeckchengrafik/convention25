from swarm import FtSwarmBase
from swarm.swarm import FtSwarmSwitch

class EmergencyStopException(Exception):
    pass

class EmergencyStop(FtSwarmSwitch):
    def __init__(self, swarm: FtSwarmBase, name: str, normally_open=True) -> None:
        super().__init__(swarm, name, normally_open)
        self._trap = False

    async def set_value(self, str_value: str) -> None:
        await super().set_value(str_value)
        if self._value:
            self._trap = True
            await self._swarm.serial_handler.send_and_wait("halt", False) # type: ignore
            raise EmergencyStopException()

    def trap(self):
        if self._trap:
            raise EmergencyStopException()
