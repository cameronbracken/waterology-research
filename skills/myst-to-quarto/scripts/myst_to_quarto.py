#!/usr/bin/env python3
"""Convert common MyST Markdown constructs to Quarto Markdown."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

CITE_ROLE = re.compile(r"\{cite(?::([a-z]+))?\}`([^`]+)`")
REF_ROLE = re.compile(r"\{(?:ref|numref)\}`([^`]+)`")
DIRECTIVE = re.compile(r"^(```|:{3,})\{([A-Za-z0-9_-]+)([^}]*)\}\s*(.*)$")
CALLOUTS = {"note", "tip", "warning", "caution", "important"}
PARENTHETICAL_ROLES = {"p", "ps"}
YEAR_ROLES = {"year", "years", "yearpar"}


def escape_attribute(value: str) -> str:
    return value.replace('"', "&quot;")


def convert_citations(text: str) -> str:
    def replace(match: re.Match[str]) -> str:
        role = match.group(1)
        keys = [key.strip() for key in re.split(r"[,;]", match.group(2)) if key.strip()]
        if role in PARENTHETICAL_ROLES:
            return "[" + "; ".join(f"@{key}" for key in keys) + "]"
        if role in YEAR_ROLES:
            return "[" + "; ".join(f"-@{key}" for key in keys) + "]"
        return " and ".join(f"@{key}" for key in keys)

    return CITE_ROLE.sub(replace, text)


def convert_figure(
    lines: list[str],
    start: int,
    argument: str,
    closing_fence: str,
    inline_options: str,
) -> tuple[list[str], int]:
    options: dict[str, str] = {}
    caption: list[str] = []
    index = start + 1
    while index < len(lines) and lines[index].strip() != closing_fence:
        line = lines[index]
        option = re.match(r"^\s*:([A-Za-z0-9_-]+):\s*(.*)$", line)
        if option:
            options[option.group(1)] = option.group(2)
        else:
            caption.append(line.strip())
        index += 1
    label = options.get("name") or options.get("label")
    attributes = [inline_options.strip()] if inline_options.strip() else []
    if label:
        attributes.append(f"#{label}")
    if alt := options.get("alt"):
        attributes.append(f'fig-alt="{escape_attribute(alt)}"')
    for option, quarto_name in (
        ("width", "width"),
        ("height", "height"),
        ("align", "fig-align"),
    ):
        if value := options.get(option):
            attributes.append(f'{quarto_name}="{escape_attribute(value)}"')
    if classes := options.get("class"):
        attributes.extend(f".{name}" for name in classes.split())
    handled = {"name", "label", "alt", "width", "height", "align", "class"}
    for option, value in options.items():
        if option not in handled:
            safe_name = re.sub(r"[^A-Za-z0-9_-]", "-", option)
            attributes.append(f'data-myst-{safe_name}="{escape_attribute(value)}"')
    suffix = "{" + " ".join(attributes) + "}" if attributes else ""
    result = [f"![{' '.join(part for part in caption if part)}]({argument}){suffix}"]
    return result, min(index + 1, len(lines))


def convert_myst(text: str) -> str:
    """Return a Quarto-compatible conversion of common MyST syntax."""
    lines = text.splitlines()
    output: list[str] = []
    index = 0
    stack: list[tuple[str, str]] = []
    while index < len(lines):
        line = lines[index]
        if stack and stack[-1][0] == "fence":
            output.append(line)
            if line.strip() == stack[-1][1]:
                stack.pop()
            index += 1
            continue
        match = DIRECTIVE.match(line)
        if match and match.group(2) == "figure":
            converted, index = convert_figure(
                lines,
                index,
                match.group(4).strip(),
                match.group(1),
                match.group(3),
            )
            output.extend(converted)
            continue
        if match and match.group(2) in CALLOUTS:
            attributes = [f".callout-{match.group(2)}"]
            if inline_options := match.group(3).strip():
                attributes.append(inline_options)
            if title := match.group(4).strip():
                escaped_title = escape_attribute(title)
                attributes.append(f'title="{escaped_title}"')
            output.append("::: {" + " ".join(attributes) + "}")
            stack.append(("callout", match.group(1)))
            index += 1
            continue
        if match:
            output.append(line)
            stack.append(("fence", match.group(1)))
            index += 1
            continue
        if stack and stack[-1][0] == "callout" and line.strip() == stack[-1][1]:
            output.append(":::")
            stack.pop()
            index += 1
            continue
        if line.lstrip().startswith("```") and line.strip() != "```":
            output.append(line)
            stack.append(("fence", "```"))
            index += 1
            continue
        converted = convert_citations(line)
        converted = REF_ROLE.sub(lambda item: f"@{item.group(1)}", converted)
        output.append(converted)
        index += 1
    return "\n".join(output) + ("\n" if text.endswith("\n") else "")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", nargs="?", type=Path)
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = args.output or args.input.with_suffix(".qmd")
    if output.resolve() == args.input.resolve():
        raise SystemExit("input and output paths must differ")
    if output.exists() and not args.force:
        raise SystemExit(f"output exists: {output}; pass --force to replace it")
    text = args.input.read_text(encoding="utf-8")
    output.write_text(convert_myst(text), encoding="utf-8")
    print(f"wrote {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
