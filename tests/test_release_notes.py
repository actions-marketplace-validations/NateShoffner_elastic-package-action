"""Unit tests for scripts/release_notes.py."""

import pytest
import yaml

import release_notes

FOOTER = (
    "Install with **Kibana > Integrations > Upload integration**, "
    "or `elastic-package install --zip <file>`."
)

ENTRIES = [
    {
        "version": "1.1.0",
        "changes": [
            {
                "description": "Add the metrics data stream",
                "type": "enhancement",
                "link": "https://github.com/owner/repo/pull/42",
            },
            {
                "description": "Fix the timestamp mapping",
                "type": "bugfix",
                "link": "https://github.com/owner/repo/pull/43",
            },
        ],
    },
    {
        "version": "1.0.0",
        "changes": [{"description": "Initial release", "type": "enhancement"}],
    },
]


def write_changelog(tmp_path, entries):
    path = tmp_path / "changelog.yml"
    path.write_text(yaml.safe_dump(entries), encoding="utf-8")
    return path


class TestRenderChange:
    def test_renders_description_and_type(self):
        change = {"description": "Initial release", "type": "enhancement"}
        assert (
            release_notes.render_change(change, "1.0.0")
            == "- Initial release (`enhancement`)"
        )

    def test_appends_pull_request_link(self):
        change = {
            "description": "Add a data stream",
            "type": "enhancement",
            "link": "https://github.com/owner/repo/pull/42",
        }
        assert release_notes.render_change(change, "1.0.0") == (
            "- Add a data stream (`enhancement`) "
            "[#42](https://github.com/owner/repo/pull/42)"
        )

    def test_tolerates_trailing_slash_in_link(self):
        change = {
            "description": "Add a data stream",
            "type": "enhancement",
            "link": "https://github.com/owner/repo/pull/42/",
        }
        assert release_notes.render_change(change, "1.0.0").endswith(
            "[#42](https://github.com/owner/repo/pull/42/)"
        )

    def test_ignores_link_without_a_numeric_tail(self):
        change = {
            "description": "Add a data stream",
            "type": "enhancement",
            "link": "https://github.com/owner/repo/issues/some-slug",
        }
        assert (
            release_notes.render_change(change, "1.0.0")
            == "- Add a data stream (`enhancement`)"
        )

    def test_ignores_empty_link(self):
        change = {"description": "Tidy up", "type": "bugfix", "link": ""}
        assert release_notes.render_change(change, "1.0.0") == "- Tidy up (`bugfix`)"

    def test_ignores_null_link(self):
        change = {"description": "Tidy up", "type": "bugfix", "link": None}
        assert release_notes.render_change(change, "1.0.0") == "- Tidy up (`bugfix`)"

    @pytest.mark.parametrize("missing", ["description", "type"])
    def test_rejects_change_missing_a_required_field(self, missing):
        change = {"description": "Tidy up", "type": "bugfix"}
        del change[missing]
        with pytest.raises(ValueError, match=missing):
            release_notes.render_change(change, "1.0.0")

    def test_rejects_change_that_is_not_a_mapping(self):
        with pytest.raises(ValueError, match="expected a mapping"):
            release_notes.render_change("Tidy up", "1.0.0")


class TestFindEntry:
    def test_finds_matching_entry(self):
        assert release_notes.find_entry(ENTRIES, "1.0.0")["version"] == "1.0.0"

    def test_returns_none_when_absent(self):
        assert release_notes.find_entry(ENTRIES, "9.9.9") is None

    def test_compares_versions_as_strings(self):
        # YAML parses an unquoted 1.0 as a float, so the comparison is on str().
        entries = [{"version": 1.0, "changes": []}]
        assert release_notes.find_entry(entries, "1.0") is entries[0]

    def test_ignores_entries_without_a_version(self):
        assert release_notes.find_entry([{"changes": []}], "1.0.0") is None


class TestRenderNotes:
    def test_renders_every_change_then_the_footer(self):
        notes, found = release_notes.render_notes(ENTRIES, "1.1.0", FOOTER)
        assert found is True
        assert notes == (
            "- Add the metrics data stream (`enhancement`) "
            "[#42](https://github.com/owner/repo/pull/42)\n"
            "- Fix the timestamp mapping (`bugfix`) "
            "[#43](https://github.com/owner/repo/pull/43)\n"
            "\n"
            f"{FOOTER}\n"
        )

    def test_renders_placeholder_for_a_missing_version(self):
        notes, found = release_notes.render_notes(ENTRIES, "2.0.0", FOOTER)
        assert found is False
        assert notes == f"No changelog entry found for 2.0.0.\n\n{FOOTER}\n"

    def test_omits_the_footer_when_empty(self):
        notes, _ = release_notes.render_notes(ENTRIES, "1.0.0")
        assert notes == "- Initial release (`enhancement`)\n"

    def test_renders_only_the_footer_for_an_entry_without_changes(self):
        notes, found = release_notes.render_notes(
            [{"version": "1.0.0"}], "1.0.0", FOOTER
        )
        assert found is True
        assert notes == f"{FOOTER}\n"

    def test_renders_nothing_for_an_entry_without_changes_or_footer(self):
        notes, found = release_notes.render_notes([{"version": "1.0.0"}], "1.0.0")
        assert found is True
        assert notes == ""


class TestLoadChangelog:
    def test_reads_entries(self, tmp_path):
        path = write_changelog(tmp_path, ENTRIES)
        assert release_notes.load_changelog(path) == ENTRIES

    def test_treats_an_empty_file_as_no_entries(self, tmp_path):
        path = tmp_path / "changelog.yml"
        path.write_text("", encoding="utf-8")
        assert release_notes.load_changelog(path) == []

    def test_rejects_a_changelog_that_is_not_a_list(self, tmp_path):
        path = tmp_path / "changelog.yml"
        path.write_text("version: 1.0.0\n", encoding="utf-8")
        with pytest.raises(ValueError, match="expected a list"):
            release_notes.load_changelog(path)

    def test_rejects_an_entry_that_is_not_a_mapping(self, tmp_path):
        path = tmp_path / "changelog.yml"
        path.write_text("- 1.0.0\n", encoding="utf-8")
        with pytest.raises(ValueError, match="entry #1"):
            release_notes.load_changelog(path)


class TestMain:
    def test_writes_notes_to_stdout(self, tmp_path, capsys):
        path = write_changelog(tmp_path, ENTRIES)
        status = release_notes.main(
            ["--changelog", str(path), "--version", "1.0.0", "--footer", FOOTER]
        )
        assert status == release_notes.EXIT_OK
        assert capsys.readouterr().out == (
            f"- Initial release (`enhancement`)\n\n{FOOTER}\n"
        )

    def test_writes_notes_to_a_file(self, tmp_path):
        path = write_changelog(tmp_path, ENTRIES)
        output = tmp_path / "notes.md"
        status = release_notes.main(
            ["--changelog", str(path), "--version", "1.0.0", "--output", str(output)]
        )
        assert status == release_notes.EXIT_OK
        assert output.read_text(encoding="utf-8") == (
            "- Initial release (`enhancement`)\n"
        )

    def test_reports_a_missing_entry_without_failing_hard(self, tmp_path, capsys):
        path = write_changelog(tmp_path, ENTRIES)
        status = release_notes.main(["--changelog", str(path), "--version", "3.0.0"])
        assert status == release_notes.EXIT_MISSING_ENTRY
        assert capsys.readouterr().out == "No changelog entry found for 3.0.0.\n"

    def test_annotates_an_unreadable_changelog(self, tmp_path, capsys):
        status = release_notes.main(
            ["--changelog", str(tmp_path / "nope.yml"), "--version", "1.0.0"]
        )
        assert status == release_notes.EXIT_ERROR
        assert "::error::" in capsys.readouterr().err

    def test_annotates_malformed_yaml(self, tmp_path, capsys):
        path = tmp_path / "changelog.yml"
        path.write_text("- version: '1.0.0'\n  changes: [\n", encoding="utf-8")
        status = release_notes.main(["--changelog", str(path), "--version", "1.0.0"])
        assert status == release_notes.EXIT_ERROR
        assert "::error::" in capsys.readouterr().err
