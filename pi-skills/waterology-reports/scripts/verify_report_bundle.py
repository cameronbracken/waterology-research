#!/usr/bin/env python3
"""Verify a Markdown report bundle against the `reports` skill structural rules.

Checks:
1. Sequential Figure numbering (`**Figure 1:**` .. `**Figure N:**`) and existence of all linked image files.
2. Sequential Table numbering (`**Table 1:**` .. `**Table N:**`) and 1-to-1 pairing (`N_figures == N_tables`).
3. Every Table is wrapped in a collapsed-by-default `<details>` block (no `open` attribute) with a
   `<summary><strong>Table k: ...</strong></summary>` header and no raw `$` LaTeX inside `<summary>`.
4. Optionally syncs `<TOPIC>_REPORT.md` -> `README.md` in the same bundle directory (`--sync-readme`).
"""

from __future__ import annotations

import argparse
import pathlib
import re
import shutil
import sys


def verify_report(md_path: pathlib.Path, sync_readme: bool = False) -> int:
    if not md_path.exists():
        print(f"[FAIL] Report file does not exist: {md_path}", file=sys.stderr)
        return 1

    text = md_path.read_text(encoding="utf-8")
    report_dir = md_path.parent
    errors: list[str] = []

    # 1. Check embedded Markdown images ![Figure k: ...](path)
    img_matches = re.findall(r"!\[([^\]]*)\]\(([^)]+)\)", text)
    for _alt_text, rel_path in img_matches:
        if rel_path.startswith(("http://", "https://")):
            continue
        img_file = (report_dir / rel_path).resolve()
        if not img_file.exists() or img_file.stat().st_size == 0:
            errors.append(f"Missing or empty figure image: {rel_path} (resolved: {img_file})")

    # 2. Check **Figure k:** captions
    fig_nums = [int(m) for m in re.findall(r"\*\*Figure\s+(\d+):\*\*", text)]
    expected_figs = list(range(1, len(fig_nums) + 1))
    if fig_nums != expected_figs:
        errors.append(
            f"Figure captions are not sequential 1..N: found {fig_nums}, expected {expected_figs}"
        )

    # 3. Check <details> blocks and **Table k:** captions
    details_open = re.findall(r"<details\s+open\b", text, flags=re.IGNORECASE)
    if details_open:
        errors.append(
            f"Found {len(details_open)} `<details open>` tag(s); tables must be collapsed by default."
        )

    summary_matches = re.findall(
        r"<summary>\s*<strong>Table\s+(\d+):([^<]*)</strong>\s*</summary>", text
    )
    summary_nums = [int(num) for num, _ in summary_matches]
    for num, s_txt in summary_matches:
        if "$" in s_txt:
            errors.append(f"Table {num} `<summary>` contains raw LaTeX `$`: {s_txt.strip()}")

    tbl_nums = [int(m) for m in re.findall(r"\*\*Table\s+(\d+):\*\*", text)]
    expected_tbls = list(range(1, len(tbl_nums) + 1))
    if tbl_nums != expected_tbls:
        errors.append(
            f"Table captions are not sequential 1..N: found {tbl_nums}, expected {expected_tbls}"
        )
    if summary_nums != expected_tbls:
        errors.append(
            f"Collapsible `<summary><strong>Table k:...</strong></summary>` headers ({summary_nums}) "
            f"do not match Table captions ({expected_tbls})"
        )

    # 4. Check 1-to-1 pairing between Figures and Tables
    if len(fig_nums) != len(tbl_nums):
        errors.append(
            f"Figure/Table count mismatch: found {len(fig_nums)} figures and {len(tbl_nums)} tables "
            "(every table must be paired 1-to-1 with a figure)."
        )

    if errors:
        print(
            f"[FAIL] {md_path.name} failed verification with {len(errors)} issue(s):",
            file=sys.stderr,
        )
        for err in errors:
            print(f"  - {err}", file=sys.stderr)
        return 1

    if sync_readme and md_path.name != "README.md":
        readme_path = report_dir / "README.md"
        shutil.copy2(md_path, readme_path)
        print(f"[OK] Synced {md_path.name} -> {readme_path.name}")

    print(
        f"[PASS] {md_path.name}: {len(fig_nums)} figures and {len(tbl_nums)} collapsible tables "
        f"verified (all images present, sequentially numbered, and paired 1-to-1)."
    )
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a Markdown report bundle.")
    parser.add_argument("report_md", type=pathlib.Path, help="Path to the Markdown report file.")
    parser.add_argument(
        "--sync-readme",
        action="store_true",
        help="Copy the verified report to README.md in the same directory.",
    )
    args = parser.parse_args()
    return verify_report(args.report_md, sync_readme=args.sync_readme)


if __name__ == "__main__":
    raise SystemExit(main())
