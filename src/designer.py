from src import colorful
from src.colorful import HarmonyType
from src.util import Aobject
from swarm import FtSwarm

class LedRange(Aobject):
    async def __init__(self, base: str, start: int, end: int, swarm: FtSwarm):
        self.leds = [await swarm.get_pixel(f"{base}{i}") for i in range(start, end + 1)]

    async def make_colorful(self, harmony: HarmonyType):
        colors = colorful.generate_related_colors(len(self.leds), harmony)
        for led, color in zip(self.leds, colors):
            await led.set_color(color)
