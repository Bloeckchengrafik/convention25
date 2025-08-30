import asyncio
import logging
from swarm import FtSwarm, FtSwarmSwitch
from swarm import FtSwarmStepper

from .sizing import Distance
from .emergency_trap import EmergencyStop
from .printer import MoveTo, Printer
from .slicer import slice
from .slicer.visualizer import visualize
from .slicer.optimizer import optimize

async def main():
    swarm = FtSwarm("/dev/ttyUSB0")
    # swarm.logger.setLevel(logging.DEBUG)
    await swarm.send("ftSwarm400", "setMicrostepMode", 2)

    y_axis: FtSwarmStepper = await swarm._get_object("ftSwarm400.M3", FtSwarmStepper)
    x_axis: FtSwarmStepper = await swarm._get_object("ftSwarm400.M4", FtSwarmStepper)
    es: EmergencyStop = await swarm._get_object("ftSwarm400.EM", EmergencyStop)

    await y_axis.set_speed(4000)
    await x_axis.set_speed(4000)

    commands = [
        MoveTo(Distance(cm=0), Distance(cm=0)),
        MoveTo(Distance(cm=1), Distance(cm=0)),
        MoveTo(Distance(cm=1), Distance(cm=1)),
        MoveTo(Distance(cm=0), Distance(cm=1)),
        MoveTo(Distance(cm=0), Distance(cm=0)),
    ] # slice("box.svg")

    printer = Printer(x_axis, y_axis, es)
    await printer.home()
    es.trap()

    for command in commands:
        await command.execute(printer)
        es.trap()

#asyncio.run(main())
visualize(optimize(slice("circuit.svg")), show=True)
