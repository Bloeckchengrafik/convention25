import random
import colorsys
from typing import List, Tuple, Literal
import math

ColorFormat = Literal['rgb', 'hex', 'hsl']
HarmonyType = Literal['analogous', 'complementary', 'triadic', 'tetradic', 'monochromatic', 'split_complementary']

def generate_related_colors(
    n: int,
    harmony_type: HarmonyType = 'analogous',
    base_hue: float | None = None,
    saturation_range: Tuple[float, float] = (0.5, 1.0),
    lightness_range: Tuple[float, float] = (0.3, 0.8),
    color_format: ColorFormat = 'hex'
) -> List[str | int | Tuple[float, float, float]]:
    """
    Generate n random colors that relate to each other using various color harmony techniques.

    Args:
        n (int): Number of colors to generate
        harmony_type (str): Type of color harmony to use
            - 'analogous': Colors adjacent on the color wheel
            - 'complementary': Colors opposite on the color wheel
            - 'triadic': Colors evenly spaced (120° apart)
            - 'tetradic': Four colors forming a rectangle on color wheel
            - 'monochromatic': Same hue with different saturation/lightness
            - 'split_complementary': Base color plus two colors adjacent to its complement
        base_hue (float): Base hue value (0-1). If None, randomly chosen
        saturation_range (tuple): Range for saturation values (0-1)
        lightness_range (tuple): Range for lightness values (0-1)
        color_format (str): Output format - 'hex', 'rgb', or 'hsl'

    Returns:
        List of colors in the specified format
    """
    if n <= 0:
        return []

    # Set base hue if not provided
    if base_hue is None:
        base_hue = random.random()

    colors = []

    if harmony_type == 'analogous':
        colors = _generate_analogous_colors(n, base_hue, saturation_range, lightness_range)
    elif harmony_type == 'complementary':
        colors = _generate_complementary_colors(n, base_hue, saturation_range, lightness_range)
    elif harmony_type == 'triadic':
        colors = _generate_triadic_colors(n, base_hue, saturation_range, lightness_range)
    elif harmony_type == 'tetradic':
        colors = _generate_tetradic_colors(n, base_hue, saturation_range, lightness_range)
    elif harmony_type == 'monochromatic':
        colors = _generate_monochromatic_colors(n, base_hue, saturation_range, lightness_range)
    elif harmony_type == 'split_complementary':
        colors = _generate_split_complementary_colors(n, base_hue, saturation_range, lightness_range)
    else:
        raise ValueError(f"Unknown harmony type: {harmony_type}")

    # Convert to requested format
    return [_convert_color_format(color, color_format) for color in colors]

def _generate_analogous_colors(n: int, base_hue: float, sat_range: Tuple[float, float], light_range: Tuple[float, float]) -> List[Tuple[float, float, float]]:
    """Generate analogous colors (adjacent on color wheel)"""
    colors = []
    angle_range = 60  # degrees on either side of base hue

    for i in range(n):
        # Spread colors within the analogous range
        if n == 1:
            hue = base_hue
        else:
            offset = (angle_range * 2 / 360) * (i / (n - 1) - 0.5)
            hue = (base_hue + offset) % 1.0

        sat = random.uniform(*sat_range)
        light = random.uniform(*light_range)
        colors.append((hue, sat, light))

    return colors

def _generate_complementary_colors(n: int, base_hue: float, sat_range: Tuple[float, float], light_range: Tuple[float, float]) -> List[Tuple[float, float, float]]:
    """Generate complementary colors (opposite on color wheel)"""
    colors = []
    complement_hue = (base_hue + 0.5) % 1.0

    for i in range(n):
        # Alternate between base and complement, with slight variations
        if i % 2 == 0:
            hue = base_hue + random.uniform(-0.05, 0.05)
        else:
            hue = complement_hue + random.uniform(-0.05, 0.05)

        hue = hue % 1.0
        sat = random.uniform(*sat_range)
        light = random.uniform(*light_range)
        colors.append((hue, sat, light))

    return colors

def _generate_triadic_colors(n: int, base_hue: float, sat_range: Tuple[float, float], light_range: Tuple[float, float]) -> List[Tuple[float, float, float]]:
    """Generate triadic colors (120° apart on color wheel)"""
    colors = []
    triadic_hues = [base_hue, (base_hue + 1/3) % 1.0, (base_hue + 2/3) % 1.0]

    for i in range(n):
        base_triadic_hue = triadic_hues[i % 3]
        hue = base_triadic_hue + random.uniform(-0.03, 0.03)
        hue = hue % 1.0

        sat = random.uniform(*sat_range)
        light = random.uniform(*light_range)
        colors.append((hue, sat, light))

    return colors

def _generate_tetradic_colors(n: int, base_hue: float, sat_range: Tuple[float, float], light_range: Tuple[float, float]) -> List[Tuple[float, float, float]]:
    """Generate tetradic colors (rectangle on color wheel)"""
    colors = []
    # Two pairs of complementary colors
    tetradic_hues = [
        base_hue,
        (base_hue + 0.25) % 1.0,
        (base_hue + 0.5) % 1.0,
        (base_hue + 0.75) % 1.0
    ]

    for i in range(n):
        base_tetradic_hue = tetradic_hues[i % 4]
        hue = base_tetradic_hue + random.uniform(-0.02, 0.02)
        hue = hue % 1.0

        sat = random.uniform(*sat_range)
        light = random.uniform(*light_range)
        colors.append((hue, sat, light))

    return colors

def _generate_monochromatic_colors(n: int, base_hue: float, sat_range: Tuple[float, float], light_range: Tuple[float, float]) -> List[Tuple[float, float, float]]:
    """Generate monochromatic colors (same hue, different saturation/lightness)"""
    colors = []

    for i in range(n):
        # Keep hue constant, vary saturation and lightness
        hue = base_hue + random.uniform(-0.01, 0.01)  # Tiny variation to avoid exact duplicates
        hue = hue % 1.0

        sat = random.uniform(*sat_range)
        light = random.uniform(*light_range)
        colors.append((hue, sat, light))

    return colors

def _generate_split_complementary_colors(n: int, base_hue: float, sat_range: Tuple[float, float], light_range: Tuple[float, float]) -> List[Tuple[float, float, float]]:
    """Generate split complementary colors"""
    colors = []
    complement = (base_hue + 0.5) % 1.0
    split_hues = [
        base_hue,
        (complement - 1/12) % 1.0,  # 30° before complement
        (complement + 1/12) % 1.0   # 30° after complement
    ]

    for i in range(n):
        base_split_hue = split_hues[i % 3]
        hue = base_split_hue + random.uniform(-0.03, 0.03)
        hue = hue % 1.0

        sat = random.uniform(*sat_range)
        light = random.uniform(*light_range)
        colors.append((hue, sat, light))

    return colors

def _convert_color_format(hsl_color: Tuple[float, float, float], format_type: ColorFormat) -> str | int | Tuple[float, float, float]:
    """Convert HSL color to requested format"""
    h, s, l = hsl_color

    if format_type == 'hsl':
        return (h, s, l)

    # Convert HSL to RGB
    r, g, b = colorsys.hls_to_rgb(h, l, s)

    if format_type == 'rgb':
        return int(r * 255) << 16 | int(g * 255) << 8 | int(b * 255)

    elif format_type == 'hex':
        return f"#{int(r * 255):02x}{int(g * 255):02x}{int(b * 255):02x}"

    else:
        raise ValueError(f"Unknown color format: {format_type}")
