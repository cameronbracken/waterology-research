import pytest

from waterology.core.report_colors import (
    DARKLY_BACKGROUND,
    LIGHT_REPORT_COLORS,
    _delta_e_2000,
    adapt_palette_chameleon,
    build_report_palette,
    contrast_ratio,
)


def test_ciede2000_matches_published_reference_pair() -> None:
    difference = _delta_e_2000((50, 2.6772, -79.7751), (50, 0, -82.7485))

    assert difference == pytest.approx(2.0425, abs=0.0001)


def test_chameleon_palette_is_seeded_and_preserves_graphic_contrast() -> None:
    first = adapt_palette_chameleon(
        LIGHT_REPORT_COLORS[:3],
        dark_background=DARKLY_BACKGROUND,
        iterations=300,
        seed=17,
    )
    second = adapt_palette_chameleon(
        LIGHT_REPORT_COLORS[:3],
        dark_background=DARKLY_BACKGROUND,
        iterations=300,
        seed=17,
    )

    assert first == second
    assert all(contrast_ratio(color, DARKLY_BACKGROUND) >= 3 for color in first)


def test_report_palette_records_light_design_and_chameleon_derivation() -> None:
    palette = build_report_palette()

    assert palette["default_mode"] == "dark"
    assert palette["light"]["colors"] == list(LIGHT_REPORT_COLORS)
    assert palette["light"]["names"] == palette["dark"]["names"]
    assert palette["dark"]["colors"] != palette["light"]["colors"]
    assert len(set(palette["dark"]["colors"])) == len(palette["dark"]["colors"])
    assert palette["algorithm"]["name"] == "Chameleon"
    assert palette["algorithm"]["seed"] == 0
    assert palette["algorithm"]["weights"] == {
        "luminance_contrast": 1.0,
        "color_consistency": 0.5,
        "adjacent_color": 1.0,
    }
    assert palette["algorithm"]["adjacency"] == "all_pairs"
    assert all(
        contrast_ratio(color, palette["dark"]["background"]) >= 3
        for color in palette["dark"]["colors"]
    )
    assert all(
        contrast_ratio(color, palette["light"]["background"]) >= 3
        for color in palette["light"]["colors"]
    )
