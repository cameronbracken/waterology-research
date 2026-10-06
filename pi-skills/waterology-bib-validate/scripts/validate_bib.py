#!/usr/bin/env python3
"""Validate citation keys and optionally verify bibliography metadata."""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from difflib import SequenceMatcher
from pathlib import Path

CITATION = re.compile(
    r"\\(?:[A-Za-z]*cite[A-Za-z]*|cite)\s*(?:\[[^]]*\]\s*){0,2}\{([^}]+)\}"
)
QUARTO_CITATION = re.compile(r"(?<![\w@])@([A-Za-z0-9][A-Za-z0-9_.:/+-]*)")
BIB_ENTRY = re.compile(r"@\w+\s*\{\s*([^,\s]+)\s*,(.*?)(?=\n@\w+\s*\{|\Z)", re.DOTALL)
SOURCE_SUFFIXES = {".tex", ".qmd", ".md", ".rmd"}
USER_AGENT = "waterology-bib-validate/0.3 (+https://codeberg.org/waterology/waterology-research)"


def edit_distance(left: str, right: str) -> int:
    """Return the Levenshtein edit distance between two strings."""
    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            current.append(
                min(
                    current[-1] + 1,
                    previous[column] + 1,
                    previous[column - 1] + (left_char != right_char),
                )
            )
        previous = current
    return previous[-1]


def citation_keys(text: str) -> set[str]:
    prose: list[str] = []
    in_fence = False
    for line in text.splitlines():
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            continue
        if not in_fence:
            prose.append(re.sub(r"`[^`]*`", "", line))
    text = "\n".join(prose)
    keys: set[str] = set()
    for match in CITATION.finditer(text):
        keys.update(key.strip() for key in match.group(1).split(",") if key.strip())
    keys.update(match.group(1).rstrip(".,;:!?") for match in QUARTO_CITATION.finditer(text))
    return keys


def bibliography_entries(text: str) -> dict[str, dict[str, str]]:
    entries: dict[str, dict[str, str]] = {}
    for match in BIB_ENTRY.finditer(text):
        entries[match.group(1)] = parse_fields(match.group(2))
    return entries


def parse_fields(body: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    index = 0
    while index < len(body):
        while index < len(body) and (body[index].isspace() or body[index] in ",}"):
            index += 1
        field = re.match(r"([A-Za-z][A-Za-z0-9_-]*)\s*=\s*", body[index:])
        if not field:
            index += 1
            continue
        name = field.group(1).lower()
        index += field.end()
        if index >= len(body):
            fields[name] = ""
            break

        if body[index] == "{":
            depth = 1
            start = index + 1
            index += 1
            while index < len(body) and depth:
                if body[index] == "{":
                    depth += 1
                elif body[index] == "}":
                    depth -= 1
                index += 1
            value = body[start : index - 1 if depth == 0 else index]
        elif body[index] == '"':
            start = index + 1
            index += 1
            while index < len(body):
                if body[index] == '"' and body[index - 1] != "\\":
                    break
                index += 1
            value = body[start:index]
            index += index < len(body)
        else:
            start = index
            while index < len(body) and body[index] not in ",\n}":
                index += 1
            value = body[start:index]
        fields[name] = " ".join(value.split())
    return fields


def suggestions(missing: str, available: set[str], distance: int) -> list[str]:
    return sorted(key for key in available if edit_distance(missing.lower(), key.lower()) == distance)


def replace_unambiguous_keys(text: str, replacements: dict[str, str]) -> str:
    def replace_latex(match: re.Match[str]) -> str:
        keys = [key.strip() for key in match.group(1).split(",")]
        updated = ",".join(replacements.get(key, key) for key in keys)
        return match.group(0).replace(match.group(1), updated, 1)

    def replace_quarto(match: re.Match[str]) -> str:
        raw = match.group(1)
        key = raw.rstrip(".,;:!?")
        return "@" + replacements.get(key, key) + raw[len(key) :]

    output: list[str] = []
    in_fence = False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith(("```", "~~~")):
            in_fence = not in_fence
            output.append(line)
            continue
        if in_fence:
            output.append(line)
            continue
        line = CITATION.sub(replace_latex, line)
        output.append(QUARTO_CITATION.sub(replace_quarto, line))
    return "".join(output)


def request_json(url: str) -> dict:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=20) as response:
        return json.load(response)


def normalize(value: str) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", value.lower()))


def first_author(value: str) -> str:
    author = value.split(" and ", 1)[0]
    if "," in author:
        return normalize(author.split(",", 1)[0])
    parts = normalize(author).split()
    return parts[-1] if parts else ""


def verify_doi(doi: str, fields: dict[str, str]) -> tuple[str, str]:
    required = {
        "title": fields.get("title", ""),
        "first author": fields.get("author", ""),
        "year": fields.get("year", ""),
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        return "UNVERIFIED", f"bibliography entry lacks {', '.join(missing)}"
    encoded = urllib.parse.quote(doi.lower().removeprefix("https://doi.org/"), safe="/")
    try:
        data = request_json(f"https://api.openalex.org/works/https://doi.org/{encoded}")
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return "FAIL", "OpenAlex did not resolve the DOI"
        return "UNVERIFIED", f"OpenAlex returned HTTP {exc.code}"
    except (OSError, TimeoutError, json.JSONDecodeError) as exc:
        return "UNVERIFIED", f"OpenAlex request failed: {exc}"
    checks: list[str] = []
    failures: list[str] = []
    unavailable: list[str] = []
    local_title = fields.get("title", "")
    remote_title = str(data.get("title") or "")
    if local_title:
        if not remote_title:
            unavailable.append("title")
        else:
            similarity = SequenceMatcher(
                None, normalize(local_title), normalize(remote_title)
            ).ratio()
            checks.append(f"title={similarity:.3f}")
            if similarity < 0.95:
                failures.append("title")
    local_author = first_author(fields.get("author", ""))
    authorships = data.get("authorships") or []
    remote_author = ""
    if authorships:
        remote_author = first_author(
            str(authorships[0].get("author", {}).get("display_name", ""))
        )
    if local_author:
        if not remote_author:
            unavailable.append("first author")
        else:
            match = local_author == remote_author
            checks.append(f"author={match}")
            if not match:
                failures.append("first author")
    local_year = fields.get("year", "")
    remote_year = str(data.get("publication_year") or "")
    if local_year:
        if not remote_year:
            unavailable.append("year")
        else:
            match = local_year == remote_year
            checks.append(f"year={match}")
            if not match:
                failures.append("year")
    detail = ", ".join(checks) or str(data.get("id", "OpenAlex record found"))
    if failures:
        return "FAIL", f"DOI resolves to mismatched {', '.join(failures)}; {detail}"
    if unavailable:
        return "UNVERIFIED", f"OpenAlex record lacks {', '.join(unavailable)}; {detail}"
    return "PASS", detail


def crossref_candidate(fields: dict[str, str]) -> tuple[str, str]:
    title = fields.get("title", "")
    if not title:
        return "WARN HIGH", "entry has no title to search"
    query = urllib.parse.urlencode({"query.title": title, "rows": 1})
    try:
        data = request_json(f"https://api.crossref.org/works?{query}")
    except (urllib.error.HTTPError, OSError, TimeoutError, json.JSONDecodeError) as exc:
        return "UNVERIFIED", f"Crossref request failed: {exc}"
    items = data.get("message", {}).get("items", [])
    if not items:
        return "WARN HIGH", "Crossref returned no candidate"
    item = items[0]
    candidate_title = " ".join(item.get("title", []))
    similarity = SequenceMatcher(None, normalize(title), normalize(candidate_title)).ratio()
    candidate_authors = item.get("author", [])
    candidate_author = normalize(candidate_authors[0].get("family", "")) if candidate_authors else ""
    issued = item.get("issued", {}).get("date-parts", [[]])
    candidate_year = str(issued[0][0]) if issued and issued[0] else ""
    matrix = (
        f"title={similarity:.3f}, "
        f"author={candidate_author == first_author(fields.get('author', ''))}, "
        f"year={candidate_year == fields.get('year', '')}, DOI={item.get('DOI', 'none')}"
    )
    return ("WARN" if similarity >= 0.95 else "WARN HIGH"), matrix


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="+", type=Path, help="source and bibliography paths")
    parser.add_argument("--verify-doi", action="store_true", help="query OpenAlex and Crossref")
    parser.add_argument("--fix", action="store_true", help="fix unique edit-distance-one keys")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bib_paths = [path for path in args.paths if path.suffix.lower() == ".bib"]
    source_paths = [path for path in args.paths if path.suffix.lower() in SOURCE_SUFFIXES]
    if not bib_paths or not source_paths:
        print("provide at least one source document and one .bib file", file=sys.stderr)
        return 2

    entries: dict[str, dict[str, str]] = {}
    for path in bib_paths:
        entries.update(bibliography_entries(path.read_text(encoding="utf-8", errors="replace")))
    available = set(entries)
    cited: set[str] = set()
    failed = False
    for path in source_paths:
        text = path.read_text(encoding="utf-8", errors="replace")
        keys = citation_keys(text)
        cited.update(keys)
        replacements: dict[str, str] = {}
        for missing in sorted(keys - available):
            likely = suggestions(missing, available, 1)
            possible = suggestions(missing, available, 2)
            if len(likely) == 1:
                print(f"{path}: {missing}: likely typo for {likely[0]}")
                replacements[missing] = likely[0]
            elif likely:
                print(f"{path}: {missing}: ambiguous likely typos: {', '.join(likely)}")
            elif possible:
                print(f"{path}: {missing}: possible typo: {', '.join(possible)}")
            else:
                print(f"{path}: {missing}: missing bibliography key")
            failed = True
        if args.fix and replacements:
            updated = replace_unambiguous_keys(text, replacements)
            path.write_text(updated, encoding="utf-8")
            print(f"fixed {len(replacements)} citation key(s) in {path}")

    unused = sorted(available - cited)
    if unused:
        print(f"unused bibliography entries: {', '.join(unused)}")

    unverified = False
    if args.verify_doi:
        for key, fields in sorted(entries.items()):
            doi = fields.get("doi")
            status, detail = verify_doi(doi, fields) if doi else crossref_candidate(fields)
            print(f"{key}: {status}: {detail}")
            failed |= status == "FAIL"
            unverified |= status == "UNVERIFIED"
    if unverified:
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
