#!/usr/bin/env python3
"""Compare a release tag against the version declared in a package manifest.

The tag is the source of truth for what gets published, but the package version
comes from manifest.yml. If the two disagree the release would be mislabelled,
so this fails loudly rather than letting a confusing artifact through.
"""

from __future__ import annotations

import argparse
import sys

import yaml

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_MISMATCH = 2


def strip_tag_prefix(tag, prefix):
    """Return the version part of a tag, without its release prefix."""
    if not tag:
        raise ValueError("no tag was provided")
    if prefix and not tag.startswith(prefix):
        raise ValueError(
            f"tag {tag!r} does not start with the expected prefix {prefix!r}"
        )
    return tag[len(prefix) :] if prefix else tag


def read_manifest_version(path):
    """Return the version declared in a package manifest.yml."""
    with open(path, encoding="utf-8") as handle:
        manifest = yaml.safe_load(handle)
    if not isinstance(manifest, dict):
        raise ValueError(
            f"{path}: expected a mapping, got {type(manifest).__name__}"
        )
    version = manifest.get("version")
    if version is None or version == "":
        raise ValueError(f"{path}: no 'version' field")
    return str(version)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Verify a release tag matches a package manifest version.",
    )
    parser.add_argument(
        "--manifest", required=True, help="path to the package manifest.yml"
    )
    parser.add_argument("--tag", required=True, help="release tag, e.g. v1.2.0")
    parser.add_argument(
        "--tag-prefix",
        default="v",
        help="prefix to strip from the tag before comparing (default: %(default)s)",
    )
    args = parser.parse_args(argv)

    try:
        tag_version = strip_tag_prefix(args.tag, args.tag_prefix)
        manifest_version = read_manifest_version(args.manifest)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"::error::{exc}", file=sys.stderr)
        return EXIT_ERROR

    if tag_version != manifest_version:
        print(
            f"::error::Tag {args.tag} resolves to version {tag_version}, but "
            f"{args.manifest} declares {manifest_version}",
            file=sys.stderr,
        )
        return EXIT_MISMATCH

    print(f"Tag {args.tag} matches {args.manifest} version {manifest_version}", file=sys.stderr)
    # Standard output stays machine readable so callers can capture the version.
    print(manifest_version)
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
