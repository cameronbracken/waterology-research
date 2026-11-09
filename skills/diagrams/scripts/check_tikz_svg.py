#!/usr/bin/env python3
"""Compile and/or verify TikZ SVG diagrams for overlaps, diagonal edges, and cramped turns.

Usage:
  python3 check_tikz_svg.py path/to/doc.md [path/to/diagram.svg ...] [--sty path/to/custom.sty]
"""

from __future__ import annotations

import argparse
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

TIKZ_COLOR_REPLACEMENTS = [
    ("#100101", "var(--m-res-fill)"),
    ("#100102", "var(--m-res-stroke)"),
    ("#100103", "var(--m-res-text)"),
    ("#100201", "var(--m-reach-fill)"),
    ("#100202", "var(--m-reach-stroke)"),
    ("#100203", "var(--m-reach-text)"),
    ("#100301", "var(--m-junc-fill)"),
    ("#100302", "var(--m-junc-stroke)"),
    ("#100303", "var(--m-junc-text)"),
    ("#100401", "var(--m-rule-fill)"),
    ("#100402", "var(--m-rule-stroke)"),
    ("#100403", "var(--m-rule-text)"),
    ("#100501", "var(--m-cond-fill)"),
    ("#100502", "var(--m-cond-stroke)"),
    ("#100503", "var(--m-cond-text)"),
    ("#100601", "var(--m-equip-fill)"),
    ("#100602", "var(--m-equip-stroke)"),
    ("#100603", "var(--m-equip-text)"),
    ("#100701", "var(--m-io-fill)"),
    ("#100702", "var(--m-io-stroke)"),
    ("#100703", "var(--m-io-text)"),
    ("#100801", "var(--m-cluster-bg)"),
    ("#100802", "var(--m-cluster-border)"),
    ("#100803", "var(--m-cluster-text)"),
    ("#100901", "var(--m-edge-bg)"),
    ("#100902", "var(--m-edge-border)"),
    ("#100903", "var(--m-edge-text)"),
    ("#100a01", "var(--m-line)"),
    ("#100A01", "var(--m-line)"),
]

NODE_FILLS = {
    "var(--m-res-fill)",
    "var(--m-reach-fill)",
    "var(--m-junc-fill)",
    "var(--m-rule-fill)",
    "var(--m-cond-fill)",
    "var(--m-equip-fill)",
    "var(--m-io-fill)",
    "#dbe7ee",
    "#dcebe5",
    "#e3ead9",
    "#efe3dc",
    "#f5ead4",
    "#e8e0ea",
    "#efece6",
}

EDGE_BG_FILLS = {"var(--m-edge-bg)", "#faf8f5"}
LINE_STROKES = {"var(--m-line)", "#575148"}
XML_COMMENT_OPEN = "".join(chr(c) for c in (60, 33, 45, 45))
XML_COMMENT_PATTERN = XML_COMMENT_OPEN + r"[^>]*-->\s*"
SVG_TAG_PATTERN = re.compile(r"(<svg\b.*?</svg>)", re.DOTALL)


def _parse_svg_path_cmds(d: str):
    tokens = re.findall(r"[A-Za-z]|[-+]?\d*\.?\d+", d)
    pts: list[tuple[float, float]] = []
    cmds: list[tuple[str, list[tuple[float, float]]]] = []
    i = 0
    cx, cy = 0.0, 0.0
    cmd = ""
    while i < len(tokens):
        if tokens[i].isalpha():
            cmd = tokens[i]
            i += 1
        if cmd in ("M", "L"):
            nx, ny = float(tokens[i]), float(tokens[i + 1])
            pts.append((nx, ny))
            cmds.append((cmd, [(cx, cy), (nx, ny)]))
            cx, cy = nx, ny
            i += 2
        elif cmd == "H":
            nx = float(tokens[i])
            pts.append((nx, cy))
            cmds.append((cmd, [(cx, cy), (nx, cy)]))
            cx = nx
            i += 1
        elif cmd == "V":
            ny = float(tokens[i])
            pts.append((cx, ny))
            cmds.append((cmd, [(cx, cy), (cx, ny)]))
            cy = ny
            i += 1
        elif cmd == "C":
            cpts = [(cx, cy)]
            for _ in range(3):
                cx, cy = float(tokens[i]), float(tokens[i + 1])
                pts.append((cx, cy))
                cpts.append((cx, cy))
                i += 2
            cmds.append(("C", cpts))
        elif cmd in ("Z", "z"):
            cmds.append((cmd, []))
        else:
            i += 1
    return pts, cmds


def _bbox_of_pts(pts: list[tuple[float, float]]) -> tuple[float, float, float, float]:
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return (min(xs), min(ys), max(xs), max(ys))


def _boxes_overlap(b1, b2, pad: float = 0.0) -> bool:
    return not (
        b1[2] + pad <= b2[0]
        or b2[2] + pad <= b1[0]
        or b1[3] + pad <= b2[1]
        or b2[3] + pad <= b1[1]
    )


def _seg_intersects_box(p1, p2, box, pad: float = 0.0) -> bool:
    x0, y0, x1, y1 = box[0] - pad, box[1] - pad, box[2] + pad, box[3] + pad
    for k in range(1, 25):
        t = k / 25.0
        px = p1[0] + t * (p2[0] - p1[0])
        py = p1[1] + t * (p2[1] - p1[1])
        if x0 < px < x1 and y0 < py < y1:
            return True
    return False


def check_tikz_svg_overlaps(svg_str: str, context_label: str = "TikZ diagram") -> None:
    """Verify that a compiled TikZ SVG has no overlaps, diagonal connectors, or cramped turns."""
    root = ET.fromstring(svg_str)
    nodes = []
    elabels = []
    edges = []
    edge_cmds = []

    def walk(el, tdepth=0, p_fill="", p_stroke="", in_defs=False):
        tag = el.tag.split("}")[-1]
        if tag == "defs":
            in_defs = True
        tr = el.attrib.get("transform", "")
        has_tr = bool(re.match(r"translate\(([-+]?\d*\.?\d+),\s*([-+]?\d*\.?\d+)\)", tr))
        cur_tdepth = tdepth + (1 if has_tr else 0)
        fill = el.attrib.get("fill", p_fill)
        stroke = el.attrib.get("stroke", p_stroke)
        if not in_defs and tag == "path" and cur_tdepth == 0:
            d = el.attrib.get("d", "")
            pts, cmds = _parse_svg_path_cmds(d)
            if pts:
                bb = _bbox_of_pts(pts)
                fl = fill.lower() if fill.startswith("#") else fill
                st = stroke.lower() if stroke.startswith("#") else stroke
                if fl in NODE_FILLS:
                    nodes.append(bb)
                elif fl in EDGE_BG_FILLS:
                    elabels.append(bb)
                elif fl == "none" and st in LINE_STROKES:
                    edges.append(pts)
                    edge_cmds.append(cmds)
        for child in el:
            walk(child, cur_tdepth, fill, stroke, in_defs)

    walk(root)
    issues = []

    for i in range(len(nodes)):
        for j in range(i + 1, len(nodes)):
            if _boxes_overlap(nodes[i], nodes[j], pad=4.0):
                issues.append(
                    f"Node {i + 1} {[round(x, 1) for x in nodes[i]]} overlaps "
                    f"Node {j + 1} {[round(x, 1) for x in nodes[j]]}"
                )
    for i, el_bb in enumerate(elabels):
        for j, n_bb in enumerate(nodes):
            if _boxes_overlap(el_bb, n_bb, pad=1.5):
                issues.append(
                    f"EdgeLabel {i + 1} {[round(x, 1) for x in el_bb]} overlaps "
                    f"Node {j + 1} {[round(x, 1) for x in n_bb]}"
                )
    for i in range(len(elabels)):
        for j in range(i + 1, len(elabels)):
            if _boxes_overlap(elabels[i], elabels[j], pad=2.0):
                issues.append(f"EdgeLabel {i + 1} overlaps EdgeLabel {j + 1}")

    for e_idx, pts in enumerate(edges):
        if len(pts) < 2:
            continue
        p_start, p_end = pts[0], pts[-1]
        for n_idx, n_bb in enumerate(nodes):
            is_ep = _boxes_overlap((*p_start, *p_start), n_bb, pad=8.0) or _boxes_overlap(
                (*p_end, *p_end), n_bb, pad=8.0
            )
            if not is_ep:
                for k in range(len(pts) - 1):
                    if _seg_intersects_box(pts[k], pts[k + 1], n_bb, pad=1.5):
                        issues.append(
                            f"Edge {e_idx + 1} segment ({pts[k][0]:.1f},{pts[k][1]:.1f})->"
                            f"({pts[k + 1][0]:.1f},{pts[k + 1][1]:.1f}) crosses/grazes "
                            f"non-endpoint Node {n_idx + 1} {[round(x, 1) for x in n_bb]}"
                        )
                        break
            else:
                for k in range(len(pts) - 1):
                    if _seg_intersects_box(pts[k], pts[k + 1], n_bb, pad=-3.0):
                        issues.append(
                            f"Edge {e_idx + 1} penetrates inside endpoint Node {n_idx + 1}"
                        )
                        break

        cmds = edge_cmds[e_idx]
        for k, (cmd, cpts) in enumerate(cmds):
            if cmd in ("L", "H", "V"):
                dx = cpts[1][0] - cpts[0][0]
                dy = cpts[1][1] - cpts[0][1]
                if abs(dx) > 0.3 and abs(dy) > 0.3:
                    issues.append(
                        f"Edge {e_idx + 1} has diagonal segment ({cpts[0][0]:.1f},{cpts[0][1]:.1f})->"
                        f"({cpts[1][0]:.1f},{cpts[1][1]:.1f}) (dx={dx:.1f}, dy={dy:.1f})"
                    )
            elif cmd == "C":
                if k + 1 < len(cmds) and cmds[k + 1][0] in ("L", "H", "V"):
                    nxt = cmds[k + 1][1]
                    sdx, sdy = nxt[1][0] - nxt[0][0], nxt[1][1] - nxt[0][1]
                    slen = math.hypot(sdx, sdy)
                    cdx, cdy = cpts[3][0] - cpts[2][0], cpts[3][1] - cpts[2][1]
                    if cdx * sdx + cdy * sdy < -0.01:
                        issues.append(
                            f"Edge {e_idx + 1} reverses direction after rounded corner (len={slen:.1f}pt)"
                        )
                    elif slen < 7.5:
                        issues.append(
                            f"Edge {e_idx + 1} has cramped straight leg ({slen:.1f}pt < 7.5pt) after rounded corner"
                        )
                if k > 0 and cmds[k - 1][0] in ("L", "H", "V"):
                    prv = cmds[k - 1][1]
                    sdx, sdy = prv[1][0] - prv[0][0], prv[1][1] - prv[0][1]
                    slen = math.hypot(sdx, sdy)
                    cdx, cdy = cpts[1][0] - cpts[0][0], cpts[1][1] - cpts[0][1]
                    if cdx * sdx + cdy * sdy < -0.01:
                        issues.append(
                            f"Edge {e_idx + 1} reverses direction before rounded corner (len={slen:.1f}pt)"
                        )
                    elif slen < 7.5:
                        issues.append(
                            f"Edge {e_idx + 1} has cramped straight leg ({slen:.1f}pt < 7.5pt) before rounded corner"
                        )

    if issues:
        joined = "\n  - ".join(issues)
        raise RuntimeError(f"TikZ geometry check failed in {context_label}:\n  - {joined}")


def extract_tikz_caption(raw_tikz: str) -> tuple[str, str]:
    captions: list[str] = []
    body_lines: list[str] = []
    for line in raw_tikz.splitlines():
        m = re.match(r"^\s*%\s*caption\s*:\s*(.+)$", line, flags=re.IGNORECASE)
        if m:
            captions.append(m.group(1).strip())
        else:
            body_lines.append(line)
    return "\n".join(body_lines), " ".join(captions)


def compile_tikz_to_svg(raw_tikz: str, sty_path: Path, context_label: str = "TikZ diagram") -> str:
    raw_without_cap, _ = extract_tikz_caption(raw_tikz)
    body = raw_without_cap.strip()
    if "\\begin{tikzpicture}" not in body:
        body = "\\begin{tikzpicture}\n" + body + "\n\\end{tikzpicture}"
    pkg_name = sty_path.stem
    tex_doc = (
        "\\documentclass[dvisvgm,tikz,border=6pt]{standalone}\n"
        "\\def\\FLOWCHARTWEB{1}\n"
        "\\def\\BARDWEB{1}\n"
        "\\def\\LLYNOPSWEB{1}\n"
        f"\\usepackage{{{pkg_name}}}\n"
        "\\begin{document}\n"
        f"{body}\n"
        "\\end{document}\n"
    )
    env = os.environ.copy()
    if Path("/Library/TeX/texbin").is_dir() and "/Library/TeX/texbin" not in env.get("PATH", ""):
        env["PATH"] = "/Library/TeX/texbin:" + env.get("PATH", "")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        shutil.copyfile(sty_path, tmp / sty_path.name)
        (tmp / "diagram.tex").write_text(tex_doc, encoding="utf-8")
        subprocess.run(
            ["latex", "-interaction=nonstopmode", "diagram.tex"],
            cwd=tmp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        subprocess.run(
            ["dvisvgm", "--no-fonts", "--zoom=1.22", "-o", "diagram.svg", "diagram.dvi"],
            cwd=tmp,
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True,
        )
        svg_str = (tmp / "diagram.svg").read_text(encoding="utf-8")

    svg_clean = re.sub(r"^<\?xml[^>]*>\s*", "", svg_str)
    svg_clean = re.sub(XML_COMMENT_PATTERN, "", svg_clean)
    for hex_code, css_var in TIKZ_COLOR_REPLACEMENTS:
        svg_clean = svg_clean.replace(hex_code, css_var).replace(hex_code.upper(), css_var)
    svg_clean = svg_clean.replace(
        "fill='#000' stroke='#000'", "fill='var(--m-io-text)' stroke='var(--m-io-text)'"
    )
    check_tikz_svg_overlaps(svg_clean, context_label=context_label)
    return svg_clean


def main() -> int:
    default_sty = Path(__file__).resolve().parent.parent / "resources" / "flowchart-tikz.sty"
    parser = argparse.ArgumentParser(description="Compile and verify TikZ diagrams.")
    parser.add_argument("paths", nargs="+", help="Markdown (.md), SVG (.svg), or HTML (.html) files")
    parser.add_argument("--sty", type=Path, default=default_sty, help="Path to TikZ .sty package")
    args = parser.parse_args()

    checked = 0
    errors = 0
    for p_str in args.paths:
        p = Path(p_str)
        if p.suffix == ".svg":
            try:
                check_tikz_svg_overlaps(p.read_text(encoding="utf-8"), context_label=str(p))
                checked += 1
            except (OSError, RuntimeError, ET.ParseError, subprocess.SubprocessError) as exc:
                print(f"FAIL: {exc}", file=sys.stderr)
                errors += 1
        elif p.suffix == ".md":
            txt = p.read_text(encoding="utf-8")
            for idx, m in enumerate(re.finditer(r"```tikz\s*\n(.*?)```", txt, re.DOTALL), 1):
                label = f"{p} (diagram {idx})"
                try:
                    compile_tikz_to_svg(m.group(1), args.sty, context_label=label)
                    checked += 1
                except (OSError, RuntimeError, ET.ParseError, subprocess.SubprocessError) as exc:
                    print(f"FAIL: {exc}", file=sys.stderr)
                    errors += 1
        elif p.suffix == ".html":
            txt = p.read_text(encoding="utf-8")
            for idx, m in enumerate(SVG_TAG_PATTERN.finditer(txt), 1):
                label = f"{p} (svg {idx})"
                try:
                    check_tikz_svg_overlaps(m.group(1), context_label=label)
                    checked += 1
                except (OSError, RuntimeError, ET.ParseError, subprocess.SubprocessError) as exc:
                    print(f"FAIL: {exc}", file=sys.stderr)
                    errors += 1

    if errors:
        print(f"FAILED: {errors} diagram(s) failed verification ({checked} passed).", file=sys.stderr)
        return 1
    print(f"PASS: {checked} TikZ diagram(s) verified with zero overlaps or turn/alignment issues.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
