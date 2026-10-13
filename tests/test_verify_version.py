"""Unit tests for scripts/verify_version.py."""

import pytest

import verify_version


def write_manifest(tmp_path, body):
    path = tmp_path / "manifest.yml"
    path.write_text(body, encoding="utf-8")
    return path


class TestStripTagPrefix:
    @pytest.mark.parametrize(
        ("tag", "prefix", "expected"),
        [
            ("v1.2.3", "v", "1.2.3"),
            ("1.2.3", "", "1.2.3"),
            ("v1.2.3", "", "v1.2.3"),
            ("release-1.2.3", "release-", "1.2.3"),
            ("v1.2.3-next", "v", "1.2.3-next"),
            ("vv1.2.3", "v", "v1.2.3"),
        ],
    )
    def test_strips_the_prefix(self, tag, prefix, expected):
        assert verify_version.strip_tag_prefix(tag, prefix) == expected

    def test_rejects_a_tag_without_the_prefix(self):
        with pytest.raises(ValueError, match="does not start with"):
            verify_version.strip_tag_prefix("1.2.3", "v")

    def test_rejects_an_empty_tag(self):
        with pytest.raises(ValueError, match="no tag"):
            verify_version.strip_tag_prefix("", "v")


class TestReadManifestVersion:
    def test_reads_the_version(self, tmp_path):
        path = write_manifest(tmp_path, 'name: my_package\nversion: "1.2.3"\n')
        assert verify_version.read_manifest_version(path) == "1.2.3"

    def test_coerces_a_non_string_version(self, tmp_path):
        # An unquoted 1.0 is a float in YAML, so comparison needs str().
        path = write_manifest(tmp_path, "name: my_package\nversion: 1.0\n")
        assert verify_version.read_manifest_version(path) == "1.0"

    def test_rejects_a_manifest_without_a_version(self, tmp_path):
        path = write_manifest(tmp_path, "name: my_package\n")
        with pytest.raises(ValueError, match="no 'version' field"):
            verify_version.read_manifest_version(path)

    def test_rejects_an_empty_version(self, tmp_path):
        path = write_manifest(tmp_path, 'name: my_package\nversion: ""\n')
        with pytest.raises(ValueError, match="no 'version' field"):
            verify_version.read_manifest_version(path)

    def test_rejects_a_manifest_that_is_not_a_mapping(self, tmp_path):
        path = write_manifest(tmp_path, "- name: my_package\n")
        with pytest.raises(ValueError, match="expected a mapping"):
            verify_version.read_manifest_version(path)

    def test_propagates_a_missing_file(self, tmp_path):
        with pytest.raises(OSError):
            verify_version.read_manifest_version(tmp_path / "nope.yml")


class TestMain:
    def test_prints_the_version_when_the_tag_matches(self, tmp_path, capsys):
        path = write_manifest(tmp_path, 'name: my_package\nversion: "1.2.3"\n')
        status = verify_version.main(["--manifest", str(path), "--tag", "v1.2.3"])
        assert status == verify_version.EXIT_OK
        assert capsys.readouterr().out == "1.2.3\n"

    def test_honours_a_custom_tag_prefix(self, tmp_path, capsys):
        path = write_manifest(tmp_path, 'name: my_package\nversion: "1.2.3"\n')
        status = verify_version.main(
            [
                "--manifest",
                str(path),
                "--tag",
                "my_package-1.2.3",
                "--tag-prefix",
                "my_package-",
            ]
        )
        assert status == verify_version.EXIT_OK
        assert capsys.readouterr().out == "1.2.3\n"

    def test_honours_an_empty_tag_prefix(self, tmp_path):
        path = write_manifest(tmp_path, 'name: my_package\nversion: "1.2.3"\n')
        status = verify_version.main(
            ["--manifest", str(path), "--tag", "1.2.3", "--tag-prefix", ""]
        )
        assert status == verify_version.EXIT_OK

    def test_annotates_a_mismatch(self, tmp_path, capsys):
        path = write_manifest(tmp_path, 'name: my_package\nversion: "1.2.3"\n')
        status = verify_version.main(["--manifest", str(path), "--tag", "v1.3.0"])
        assert status == verify_version.EXIT_MISMATCH
        captured = capsys.readouterr()
        assert "::error::" in captured.err
        assert "1.3.0" in captured.err and "1.2.3" in captured.err
        assert captured.out == ""

    def test_annotates_a_tag_missing_the_prefix(self, tmp_path, capsys):
        path = write_manifest(tmp_path, 'name: my_package\nversion: "1.2.3"\n')
        status = verify_version.main(["--manifest", str(path), "--tag", "1.2.3"])
        assert status == verify_version.EXIT_ERROR
        assert "::error::" in capsys.readouterr().err

    def test_annotates_a_missing_manifest(self, tmp_path, capsys):
        status = verify_version.main(
            ["--manifest", str(tmp_path / "nope.yml"), "--tag", "v1.2.3"]
        )
        assert status == verify_version.EXIT_ERROR
        assert "::error::" in capsys.readouterr().err
