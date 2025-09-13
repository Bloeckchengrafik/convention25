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
    def execute(self, printer: 'Printer'):
        pass

@dataclass
class MoveTo(Command):
    x: Distance
    y: Distance

    def execute(self, printer: 'Printer'):
        printer.ingress_command(self.x, self.y, False)

@dataclass
class ExtrudeTo(Command):
    x: Distance
    y: Distance

    def execute(self, printer: 'Printer'):
        printer.ingress_command(self.x, self.y, True)

@dataclass
class SwitchTool(Command):
    tool_id: int

    def execute(self, printer: 'Printer'):
        pass

@dataclass
class ToolTiming:
    lead_time: float  # seconds to start tool early
    lag_time: float   # seconds to stop tool early
    retraction_distance: int  # steps to retract during travel
    retraction_speed: int     # speed for retraction moves

@dataclass
class MotorConfiguration:
    motor: FtSwarmStepper
    steps: int
    speed: int

@dataclass
class ControlPoint:
    x: MotorConfiguration
    y: MotorConfiguration
    tool: MotorConfiguration | None

@dataclass
class TimedControlPoint:
    x: MotorConfiguration
    y: MotorConfiguration
    tool: MotorConfiguration | None
    start_time: float
    duration: float
    is_retraction: bool = False

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
        self.config = config
        self.control_points: list[ControlPoint] = []
        self.tool_timing = ToolTiming(
            lead_time=config.tool_lead_time,
            lag_time=config.tool_lag_time,
            retraction_distance=config.retraction_distance,
            retraction_speed=config.retraction_speed
        )
        self.timed_control_points: list[TimedControlPoint] = []
        self.last_was_extrusion = False
        self.execution_start_time = 0

    def update_tool_timing(self, lead_time: float, lag_time: float, retraction_distance: int, retraction_speed: int):
        """Update tool timing configuration dynamically"""
        self.tool_timing.lead_time = lead_time
        self.tool_timing.lag_time = lag_time
        self.tool_timing.retraction_distance = retraction_distance
        self.tool_timing.retraction_speed = retraction_speed

    async def home(self, do_finalize = True):
        #await self.swarm.set_microstep_mode(Io.PRIMARY_PWRDRIVE, MicrostepMode.FULL)
        await self.y_axis.set_speed(3000)
        await self.x_axis.set_speed(7000)
        await self.y_axis.set_homing_offset(1000)
        await self.x_axis.set_homing_offset(-1000)
        await self.x_axis.homing_and_wait(-500000)
        self.es.trap()
        await self.y_axis.homing_and_wait(500000)
        self.es.trap()

        #await self.swarm.set_microstep_mode(Io.PRIMARY_PWRDRIVE, MicrostepMode.HALF)
        if not do_finalize:
            return
        await self.y_axis.set_distance(-(Distance(cm=11, mm=0).to_steps(1)), True)
        await self.y_axis.run_and_wait()
        self.es.trap()

        await self.x_axis.set_distance(Distance(cm=7, mm=0).to_steps(1), True)
        await self.x_axis.run_and_wait()
        self.es.trap()

    def ingress_command(self, x: Distance, y: Distance, should_extrude: bool):
        target_x = -x.to_steps(1)
        target_y = y.to_steps(1)

        dx = target_x - self.step_x
        dy = target_y - self.step_y

        # Add retraction if switching from extrusion to travel
        if self.last_was_extrusion and not should_extrude:
            self._add_retraction_move()

        # Add prime if switching from travel to extrusion
        if not self.last_was_extrusion and should_extrude:
            self._add_prime_move()

        self.step_x = target_x
        self.step_y = target_y

        distance = math.sqrt(dx**2 + dy**2)
        if distance == 0:
            return

        angle_rad = math.atan2(dy, dx)
        vx = self.speed * math.cos(angle_rad)
        vy = self.speed * math.sin(angle_rad)

        # Calculate movement time
        time_x = abs(dx) / abs(vx) if vx != 0 else 0
        time_y = abs(dy) / abs(vy) if vy != 0 else 0
        movement_time = max(time_x, time_y)

        tool_config = None
        if should_extrude:
            tool = self.tools[self.tool]
            steps = int(abs(distance) * self.config.flow_rate)
            tool_speed = max(abs(int(steps / movement_time) if movement_time > 0 else 0), 50)
            tool_config = MotorConfiguration(tool, steps, tool_speed)
            print(f" # Tool: {tool} > {steps} steps > {abs(tool_speed)} speed")

        x_config = MotorConfiguration(self.x_axis, int(abs(dx)), int(abs(vx)))
        y_config = MotorConfiguration(self.y_axis, int(abs(dy)), int(abs(vy)))
        print(f"MoveTo: {dx}/{abs(int(vx))} {dy}/{abs(int(vy))} {should_extrude}")

        # Calculate start time for this move (relative to execution start)
        current_time = sum(cp.duration for cp in self.timed_control_points)

        timed_point = TimedControlPoint(
            x=x_config,
            y=y_config,
            tool=tool_config,
            start_time=current_time,
            duration=movement_time
        )

        self.timed_control_points.append(timed_point)
        self.control_points.append(ControlPoint(x_config, y_config, tool_config))
        self.last_was_extrusion = should_extrude

    def _add_retraction_move(self):
        """Add a retraction move to prevent spillage during travel"""
        tool = self.tools[self.tool]
        retraction_config = MotorConfiguration(
            tool,
            -self.tool_timing.retraction_distance,  # Negative for retraction
            self.tool_timing.retraction_speed
        )

        current_time = sum(cp.duration for cp in self.timed_control_points)
        retraction_time = abs(self.tool_timing.retraction_distance) / self.tool_timing.retraction_speed

        retraction_point = TimedControlPoint(
            x=MotorConfiguration(self.x_axis, 0, 0),  # No axis movement
            y=MotorConfiguration(self.y_axis, 0, 0),
            tool=retraction_config,
            start_time=current_time,
            duration=retraction_time,
            is_retraction=True
        )

        self.timed_control_points.append(retraction_point)

    def _add_prime_move(self):
        """Add a prime move to prepare for extrusion"""
        tool = self.tools[self.tool]
        prime_config = MotorConfiguration(
            tool,
            self.tool_timing.retraction_distance,  # Positive to prime
            self.tool_timing.retraction_speed
        )

        current_time = sum(cp.duration for cp in self.timed_control_points)
        prime_time = self.tool_timing.retraction_distance / self.tool_timing.retraction_speed

        prime_point = TimedControlPoint(
            x=MotorConfiguration(self.x_axis, 0, 0),
            y=MotorConfiguration(self.y_axis, 0, 0),
            tool=prime_config,
            start_time=current_time,
            duration=prime_time,
            is_retraction=True
        )

        self.timed_control_points.append(prime_point)

    async def axis_controller(self, motor: FtSwarmStepper, command_buffer):
        """Controller for X or Y axis motors"""
        import asyncio

        while True:
            try:
                command = await command_buffer.get()
                if command is None:  # Shutdown signal
                    break

                motor_config, start_time = command

                # Wait until it's time to start this command
                current_time = asyncio.get_event_loop().time() - self.execution_start_time
                if start_time > current_time:
                    await asyncio.sleep(start_time - current_time)

                # Execute the movement
                if motor_config.steps > 0:
                    await motor_config.motor.set_speed(motor_config.speed)
                    await motor_config.motor.set_distance(motor_config.steps, True)
                    await motor_config.motor.run_and_wait()
                    self.es.trap()

                command_buffer.task_done()

            except Exception as e:
                print(f"Axis controller error: {e}")
                break

    async def tool_controller(self, motor: FtSwarmStepper, command_buffer):
        """Controller for tool motors with lead/lag compensation"""
        import asyncio

        while True:
            try:
                command = await command_buffer.get()
                if command is None:  # Shutdown signal
                    break

                motor_config, start_time, duration, is_retraction = command

                # Calculate adjusted timing for tool
                if not is_retraction:
                    adjusted_start = start_time - self.tool_timing.lead_time
                    adjusted_duration = duration - self.tool_timing.lag_time
                else:
                    # Retraction moves use normal timing
                    adjusted_start = start_time
                    adjusted_duration = duration

                # Wait until it's time to start
                current_time = asyncio.get_event_loop().time() - self.execution_start_time
                if adjusted_start > current_time:
                    await asyncio.sleep(adjusted_start - current_time)

                # Execute the tool movement
                if motor_config.steps != 0:
                    await motor_config.motor.set_speed(motor_config.speed)
                    await motor_config.motor.set_distance(motor_config.steps, True)

                    # For non-retraction moves, stop early
                    if not is_retraction and adjusted_duration > 0:
                        # Start the movement but don't wait for completion
                        await motor_config.motor.run()
                        await asyncio.sleep(adjusted_duration)
                        await motor_config.motor.stop()
                    else:
                        # For retractions, wait for completion
                        await motor_config.motor.run_and_wait()

                    self.es.trap()

                command_buffer.task_done()

            except Exception as e:
                print(f"Tool controller error: {e}")
                break

    async def execute(self):
        """Execute all queued control points with coordinated timing"""
        import asyncio

        if not self.timed_control_points:
            return

        # Create command buffers
        x_buffer = asyncio.Queue()
        y_buffer = asyncio.Queue()
        tool_buffer = asyncio.Queue()

        # Start controllers
        x_task = asyncio.create_task(self.axis_controller(self.x_axis, x_buffer))
        y_task = asyncio.create_task(self.axis_controller(self.y_axis, y_buffer))
        tool_task = asyncio.create_task(self.tool_controller(self.tools[self.tool], tool_buffer))

        try:
            # Record execution start time
            self.execution_start_time = asyncio.get_event_loop().time()

            # Queue all commands
            for point in self.timed_control_points:
                # Queue axis commands
                await x_buffer.put((point.x, point.start_time))
                await y_buffer.put((point.y, point.start_time))

                # Queue tool command if present
                if point.tool:
                    await tool_buffer.put((
                        point.tool,
                        point.start_time,
                        point.duration,
                        point.is_retraction
                    ))

            # Wait for all commands to complete
            await x_buffer.join()
            await y_buffer.join()
            await tool_buffer.join()

        finally:
            # Shutdown controllers
            await x_buffer.put(None)
            await y_buffer.put(None)
            await tool_buffer.put(None)

            await asyncio.gather(x_task, y_task, tool_task, return_exceptions=True)

            # Clear the processed points
            self.timed_control_points.clear()
