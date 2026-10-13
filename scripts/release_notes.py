#!/usr/bin/env python3
"""Render the changelog.yml entry for one package version as markdown.

Elastic package changelogs are a list of entries, newest first:

    - version: "1.2.0"
      changes:
        - description: Add the metrics data stream
          type: enhancement
          link: https://github.com/owner/repo/pull/42

This renders a single entry as a markdown bullet list suitable for GitHub
release notes. An exit status of 2 means the changelog has no entry for the
requested version: placeholder notes are still written, so the caller decides
whether a missing entry is fatal.
"""

from __future__ import annotations

import argparse
import sys

import yaml

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_MISSING_ENTRY = 2


def load_changelog(path):
    """Read a changelog.yml file and return its list of entries."""
    with open(path, encoding="utf-8") as handle:
        entries = yaml.safe_load(handle)
    if entries is None:
        return []
    if not isinstance(entries, list):
        raise ValueError(
            f"{path}: expected a list of changelog entries, "
            f"got {type(entries).__name__}"
        )
    for position, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ValueError(
                f"{path}: changelog entry #{position + 1} is a "
                f"{type(entry).__name__}, expected a mapping"
            )
    return entries


def find_entry(entries, version):
    """Return the entry for a version, or None when there is no such entry."""
    # Versions are compared as strings because YAML parses an unquoted 1.0 as a
    # float, and the caller's version always arrives as a string.
    wanted = str(version)
    return next((e for e in entries if str(e.get("version")) == wanted), None)


def render_change(change, version):
    """Render one change of an entry as a markdown list item."""
    if not isinstance(change, dict):
        raise ValueError(
            f"changelog entry {version} has a change that is a "
            f"{type(change).__name__}, expected a mapping"
        )
    try:
        description = change["description"]
        change_type = change["type"]
    except KeyError as exc:
        raise ValueError(
            f"changelog entry {version} has a change missing the "
            f"{exc.args[0]!r} field"
        ) from exc

    line = f"- {description} (`{change_type}`)"
    link = change.get("link") or ""
    # Only pull-request style links get a short [#123] label; anything else is
    # left out rather than rendered as a bare URL.
    number = link.rstrip("/").rsplit("/", 1)[-1]
    if link and number.isdigit():
        line += f" [#{number}]({link})"
    return line


def render_notes(entries, version, footer=""):
    """Render the notes for a version, returning (markdown, entry_was_found)."""
    entry = find_entry(entries, version)
    if entry is None:
        body = [f"No changelog entry found for {version}."]
    else:
        body = [render_change(c, version) for c in entry.get("changes") or []]

    sections = []
    if body:
        sections.append("\n".join(body))
    if footer:
        sections.append(footer)

    text = "\n\n".join(sections).strip("\n")
    return (text + "\n" if text else ""), entry is not None


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Render a changelog.yml entry as markdown release notes.",
    )
    parser.add_argument(
        "--changelog", required=True, help="path to the package changelog.yml"
    )
    parser.add_argument(
        "--version", required=True, help="package version to render notes for"
    )
    parser.add_argument(
        "--footer", default="", help="markdown appended after the changelog body"
    )
    parser.add_argument(
        "--output", help="file to write the notes to (default: standard output)"
    )
    args = parser.parse_args(argv)

    try:
        entries = load_changelog(args.changelog)
        notes, found = render_notes(entries, args.version, args.footer)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_ERROR

    if args.output:
        with open(args.output, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(notes)
    else:
        sys.stdout.write(notes)

    return EXIT_OK if found else EXIT_MISSING_ENTRY


if __name__ == "__main__":
    sys.exit(main())
