from pathlib import Path


def _luminance(color: str) -> float:
    channels = [int(color[index : index + 2], 16) / 255 for index in (1, 3, 5)]
    values = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * values[0] + 0.7152 * values[1] + 0.0722 * values[2]


def _contrast(first: str, second: str) -> float:
    bright, dark = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (bright + 0.05) / (dark + 0.05)


def test_dark_theme_button_colors_meet_text_contrast() -> None:
    css = (Path(__file__).parents[2] / "src/waterology/dashboard/static/dashboard.css").read_text(
        encoding="utf-8"
    )

    assert css.count("--accent: #356859;") == 3
    assert css.count("--danger: #8f3e32;") == 3
    assert css.count("--button-hover: #274f43;") == 2
    assert _contrast("#356859", "#ffffff") >= 4.5
    assert _contrast("#8f3e32", "#ffffff") >= 4.5
    assert _contrast("#274f43", "#ffffff") >= 4.5
    assert "@media (max-width: 820px)" in css
    assert ".skip-link:focus" in css
