"""Light-first report palettes adapted to dark mode with Chameleon's objective.

The implementation follows the method described by Karunathilaka et al. (2025)
without copying the source notebook. See ATTRIBUTION.md.
"""

from __future__ import annotations

import math
import random
from collections.abc import Iterable, Sequence
from functools import lru_cache
from itertools import combinations

LIGHT_REPORT_BACKGROUND = "#FFFFFF"
DARKLY_BACKGROUND = "#222222"
LIGHT_REPORT_FOREGROUND = "#2C3E50"
DARK_REPORT_FOREGROUND = "#F4F1EA"
LIGHT_REPORT_GRID = "#D9DED8"
DARK_REPORT_GRID = "#4B514C"

# Earth tones with distinct hues and at least 3:1 contrast against white.
LIGHT_REPORT_COLORS = (
    "#5F7654",  # moss
    "#A04732",  # clay
    "#8A6418",  # ochre
    "#2F6F89",  # lake
    "#765071",  # plum
    "#2A7772",  # teal
)
LIGHT_REPORT_COLOR_NAMES = ("moss", "clay", "ochre", "lake", "plum", "teal")

_D65 = (0.95047, 1.0, 1.08883)
_CHAMELEON_WEIGHTS = (1.0, 0.5, 1.0)
_CHAMELEON_ITERATIONS = 20_000
_MIN_GRAPHIC_CONTRAST = 3.0


def _hex_to_rgb(color: str) -> tuple[float, float, float]:
    value = color.removeprefix("#")
    if len(value) != 6:
        raise ValueError(f"Expected a six-digit hex color, got {color!r}")
    try:
        return tuple(int(value[index : index + 2], 16) / 255 for index in (0, 2, 4))
    except ValueError as error:
        raise ValueError(f"Invalid hex color {color!r}") from error


def _rgb_to_hex(rgb: Sequence[float]) -> str:
    return "#" + "".join(f"{round(max(0, min(1, channel)) * 255):02X}" for channel in rgb)


def _linearize(channel: float) -> float:
    return channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4


def _encode_srgb(channel: float) -> float:
    return 12.92 * channel if channel <= 0.0031308 else 1.055 * channel ** (1 / 2.4) - 0.055


def _rgb_to_lab(rgb: Sequence[float]) -> tuple[float, float, float]:
    red, green, blue = (_linearize(channel) for channel in rgb)
    xyz = (
        red * 0.4124564 + green * 0.3575761 + blue * 0.1804375,
        red * 0.2126729 + green * 0.7151522 + blue * 0.0721750,
        red * 0.0193339 + green * 0.1191920 + blue * 0.9503041,
    )

    def transform(value: float) -> float:
        return value ** (1 / 3) if value > 216 / 24389 else (24389 / 27 * value + 16) / 116

    x, y, z = (transform(value / white) for value, white in zip(xyz, _D65, strict=True))
    return 116 * y - 16, 500 * (x - y), 200 * (y - z)


def _lab_to_rgb(lab: Sequence[float]) -> tuple[float, float, float]:
    lightness, a_value, b_value = lab
    fy = (lightness + 16) / 116
    fx = fy + a_value / 500
    fz = fy - b_value / 200

    def inverse(value: float) -> float:
        cube = value**3
        return cube if cube > 216 / 24389 else (116 * value - 16) / (24389 / 27)

    x, y, z = (
        inverse(component) * white for component, white in zip((fx, fy, fz), _D65, strict=True)
    )
    linear = (
        x * 3.2404542 + y * -1.5371385 + z * -0.4985314,
        x * -0.9692660 + y * 1.8760108 + z * 0.0415560,
        x * 0.0556434 + y * -0.2040259 + z * 1.0572252,
    )
    return tuple(_encode_srgb(channel) for channel in linear)


def _lab_to_lch(lab: Sequence[float]) -> tuple[float, float, float]:
    lightness, a_value, b_value = lab
    return lightness, math.hypot(a_value, b_value), math.degrees(math.atan2(b_value, a_value)) % 360


def _lch_to_lab(lch: Sequence[float]) -> tuple[float, float, float]:
    lightness, chroma, hue = lch
    angle = math.radians(hue)
    return lightness, chroma * math.cos(angle), chroma * math.sin(angle)


def _displayable_rgb(lch: Sequence[float]) -> tuple[float, float, float] | None:
    rgb = _lab_to_rgb(_lch_to_lab(lch))
    if all(0 <= channel <= 1 for channel in rgb):
        return rgb
    return None


def _relative_luminance(color: str) -> float:
    red, green, blue = (_linearize(channel) for channel in _hex_to_rgb(color))
    return 0.2126 * red + 0.7152 * green + 0.0722 * blue


def contrast_ratio(first: str, second: str) -> float:
    """Return the WCAG contrast ratio between two sRGB hex colors."""

    lighter, darker = sorted(
        (_relative_luminance(first), _relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _delta_e_2000(first: Sequence[float], second: Sequence[float]) -> float:
    l1, a1, b1 = first
    l2, a2, b2 = second
    c1 = math.hypot(a1, b1)
    c2 = math.hypot(a2, b2)
    mean_c = (c1 + c2) / 2
    adjustment = 0.5 * (1 - math.sqrt(mean_c**7 / (mean_c**7 + 25**7)))
    a1_prime = (1 + adjustment) * a1
    a2_prime = (1 + adjustment) * a2
    c1_prime = math.hypot(a1_prime, b1)
    c2_prime = math.hypot(a2_prime, b2)
    h1_prime = math.degrees(math.atan2(b1, a1_prime)) % 360
    h2_prime = math.degrees(math.atan2(b2, a2_prime)) % 360

    delta_l = l2 - l1
    delta_c = c2_prime - c1_prime
    if c1_prime * c2_prime == 0:
        delta_h_angle = 0.0
    else:
        delta_h_angle = h2_prime - h1_prime
        if delta_h_angle > 180:
            delta_h_angle -= 360
        elif delta_h_angle < -180:
            delta_h_angle += 360
    delta_h = 2 * math.sqrt(c1_prime * c2_prime) * math.sin(math.radians(delta_h_angle / 2))

    mean_l = (l1 + l2) / 2
    mean_c_prime = (c1_prime + c2_prime) / 2
    if c1_prime * c2_prime == 0:
        mean_h = h1_prime + h2_prime
    elif abs(h1_prime - h2_prime) <= 180:
        mean_h = (h1_prime + h2_prime) / 2
    elif h1_prime + h2_prime < 360:
        mean_h = (h1_prime + h2_prime + 360) / 2
    else:
        mean_h = (h1_prime + h2_prime - 360) / 2

    hue_term = (
        1
        - 0.17 * math.cos(math.radians(mean_h - 30))
        + 0.24 * math.cos(math.radians(2 * mean_h))
        + 0.32 * math.cos(math.radians(3 * mean_h + 6))
        - 0.20 * math.cos(math.radians(4 * mean_h - 63))
    )
    delta_theta = 30 * math.exp(-(((mean_h - 275) / 25) ** 2))
    rotation = 2 * math.sqrt(mean_c_prime**7 / (mean_c_prime**7 + 25**7))
    scale_l = 1 + 0.015 * (mean_l - 50) ** 2 / math.sqrt(20 + (mean_l - 50) ** 2)
    scale_c = 1 + 0.045 * mean_c_prime
    scale_h = 1 + 0.015 * mean_c_prime * hue_term
    rotation_term = -math.sin(math.radians(2 * delta_theta)) * rotation
    return math.sqrt(
        (delta_l / scale_l) ** 2
        + (delta_c / scale_c) ** 2
        + (delta_h / scale_h) ** 2
        + rotation_term * (delta_c / scale_c) * (delta_h / scale_h)
    )


def _adjacent_pairs(count: int) -> tuple[tuple[int, int], ...]:
    # Report series can meet in any order, so every pair is treated as adjacent.
    return tuple(combinations(range(count), 2))


def _energy(
    light: Sequence[Sequence[float]],
    dark: Sequence[Sequence[float]],
    light_background_l: float,
    dark_background_l: float,
    adjacent: Iterable[tuple[int, int]],
) -> float:
    luminance_loss = sum(
        abs(abs(light_background_l - source[0]) - abs(candidate[0] - dark_background_l)) / 100
        for source, candidate in zip(light, dark, strict=True)
    ) / len(light)
    color_loss = sum(
        _delta_e_2000(source, candidate) / 124
        for source, candidate in zip(light, dark, strict=True)
    ) / len(light)
    adjacent_pairs = tuple(adjacent)
    adjacent_loss = (
        sum(
            abs(
                _delta_e_2000(light[first], light[second])
                - _delta_e_2000(dark[first], dark[second])
            )
            / 124
            for first, second in adjacent_pairs
        )
        / len(adjacent_pairs)
        if adjacent_pairs
        else 0.0
    )
    return (
        _CHAMELEON_WEIGHTS[0] * luminance_loss
        + _CHAMELEON_WEIGHTS[1] * color_loss
        + _CHAMELEON_WEIGHTS[2] * adjacent_loss
    )


def _initial_dark_color(
    source_lab: Sequence[float],
    light_background_l: float,
    dark_background_l: float,
    dark_background: str,
) -> tuple[float, float, float]:
    source_lch = _lab_to_lch(source_lab)
    target_l = min(100.0, dark_background_l + abs(light_background_l - source_lab[0]))
    for step in range(101):
        candidate = (target_l, source_lch[1] * (1 - step / 100), source_lch[2])
        rgb = _displayable_rgb(candidate)
        if (
            rgb is not None
            and contrast_ratio(_rgb_to_hex(rgb), dark_background) >= _MIN_GRAPHIC_CONTRAST
        ):
            return candidate
    raise ValueError("The light palette cannot be mapped into the dark sRGB gamut")


def adapt_palette_chameleon(
    colors: Sequence[str],
    *,
    light_background: str = LIGHT_REPORT_BACKGROUND,
    dark_background: str = DARKLY_BACKGROUND,
    iterations: int = _CHAMELEON_ITERATIONS,
    seed: int = 0,
) -> tuple[str, ...]:
    """Transform a light palette with Chameleon's seeded annealing objective.

    Chameleon's three published losses are retained. Waterology adds a 3:1
    feasibility constraint for data marks so a transformed color is not accepted
    when it is illegible against the Darkly background.
    """

    if not colors:
        raise ValueError("At least one source color is required")
    if iterations < 0:
        raise ValueError("Iterations must be nonnegative")
    light_labs = tuple(_rgb_to_lab(_hex_to_rgb(color)) for color in colors)
    light_lchs = tuple(_lab_to_lch(color) for color in light_labs)
    light_background_l = _rgb_to_lab(_hex_to_rgb(light_background))[0]
    dark_background_l = _rgb_to_lab(_hex_to_rgb(dark_background))[0]
    current = [
        _initial_dark_color(source, light_background_l, dark_background_l, dark_background)
        for source in light_labs
    ]
    adjacent = _adjacent_pairs(len(colors))
    current_energy = _energy(light_labs, current, light_background_l, dark_background_l, adjacent)
    best = list(current)
    best_energy = current_energy
    temperature = 10_000.0
    rng = random.Random()
    rng.seed(seed)

    for _ in range(iterations):
        index = rng.randrange(len(current))
        proposal = list(current)
        candidate = list(proposal[index])
        component = rng.randrange(3)
        if component == 0:
            candidate[0] = max(0.0, min(100.0, candidate[0] + rng.uniform(-20, 20)))
        elif component == 1:
            candidate[1] = max(0.0, min(100.0, candidate[1] + rng.uniform(-20, 20)))
        else:
            candidate[2] = max(0.0, min(360.0, candidate[2] + rng.uniform(-50, 50)))
        source_lch = light_lchs[index]
        hue_difference = abs(candidate[2] - source_lch[2])
        hue_difference = min(hue_difference, 360 - hue_difference)
        if hue_difference > 20 or candidate[1] < source_lch[1] * 0.7:
            temperature *= 0.99
            continue
        rgb = _displayable_rgb(candidate)
        if rgb is None or contrast_ratio(_rgb_to_hex(rgb), dark_background) < _MIN_GRAPHIC_CONTRAST:
            temperature *= 0.99
            continue
        proposal[index] = tuple(candidate)
        proposal_energy = _energy(
            light_labs, proposal, light_background_l, dark_background_l, adjacent
        )
        difference = proposal_energy - current_energy
        if difference < 0 or rng.random() < math.exp(-difference / max(temperature, 1e-12)):
            current = proposal
            current_energy = proposal_energy
            if proposal_energy < best_energy:
                best = list(proposal)
                best_energy = proposal_energy
        temperature *= 0.99

    transformed = []
    for color in best:
        rgb = _displayable_rgb(color)
        if rgb is None:
            raise RuntimeError("Chameleon returned a color outside the sRGB gamut")
        transformed.append(_rgb_to_hex(rgb))
    return tuple(transformed)


@lru_cache(maxsize=1)
def _default_dark_colors() -> tuple[str, ...]:
    return adapt_palette_chameleon(LIGHT_REPORT_COLORS)


def build_report_palette() -> dict:
    """Return the report palette and enough metadata to audit its derivation."""

    return {
        "schema_version": 1,
        "default_mode": "dark",
        "light": {
            "theme": "flatly",
            "background": LIGHT_REPORT_BACKGROUND,
            "foreground": LIGHT_REPORT_FOREGROUND,
            "grid": LIGHT_REPORT_GRID,
            "names": list(LIGHT_REPORT_COLOR_NAMES),
            "colors": list(LIGHT_REPORT_COLORS),
        },
        "dark": {
            "theme": "darkly",
            "background": DARKLY_BACKGROUND,
            "foreground": DARK_REPORT_FOREGROUND,
            "grid": DARK_REPORT_GRID,
            "names": list(LIGHT_REPORT_COLOR_NAMES),
            "colors": list(_default_dark_colors()),
        },
        "algorithm": {
            "name": "Chameleon",
            "paper": "https://doi.org/10.1145/3786995.3787017",
            "repository": "https://github.com/VIDA-Lab/Chameleon",
            "seed": 0,
            "iterations": _CHAMELEON_ITERATIONS,
            "weights": {
                "luminance_contrast": _CHAMELEON_WEIGHTS[0],
                "color_consistency": _CHAMELEON_WEIGHTS[1],
                "adjacent_color": _CHAMELEON_WEIGHTS[2],
            },
            "adjacency": "all_pairs",
            "waterology_minimum_graphic_contrast": _MIN_GRAPHIC_CONTRAST,
            "waterology_maximum_hue_shift_degrees": 20,
            "waterology_minimum_chroma_fraction": 0.7,
        },
    }
