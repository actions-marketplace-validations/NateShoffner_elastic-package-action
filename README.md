# elastic-package action

Install the [`elastic-package`](https://github.com/elastic/elastic-package) CLI
on a GitHub Actions runner, and release Elastic integration packages without
hand-rolling the same shell in every repository.

| Action | Reference | What it does |
| --- | --- | --- |
| Setup elastic-package | `NateShoffner/elastic-package-action@v1` | Downloads a pinned release, verifies it against the published checksums, caches it, and puts it on `PATH`. |
| Verify package version | `NateShoffner/elastic-package-action/verify-version@v1` | Fails the job when the release tag disagrees with the `version` in `manifest.yml`. |
| Render package release notes | `NateShoffner/elastic-package-action/release-notes@v1` | Renders the `changelog.yml` entry for a version as markdown for `gh release create --notes-file`. |

Only the root action is listed on the Marketplace; the other two are referenced
by their subpath, as above.

```yaml
- uses: NateShoffner/elastic-package-action@v1
- run: elastic-package check -v
```

A release workflow using all three:

```yaml
name: Release

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  release:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: packages/my_package
    steps:
      - uses: actions/checkout@v7

      - uses: NateShoffner/elastic-package-action@v1
        with:
          version: v0.126.4

      - uses: NateShoffner/elastic-package-action/verify-version@v1
        with:
          manifest-path: packages/my_package/manifest.yml

      - run: elastic-package check -v

      - uses: NateShoffner/elastic-package-action/release-notes@v1
        id: notes
        with:
          changelog-path: packages/my_package/changelog.yml

      - env:
          GH_TOKEN: ${{ github.token }}
        run: |
          gh release create "$GITHUB_REF_NAME" \
            build/packages/*.zip \
            --title "$GITHUB_REF_NAME" \
            --notes-file "${{ steps.notes.outputs.notes-file }}"
```

`working-directory` does not apply to `uses:` steps, so the subpath actions take
explicit paths.

## Setup elastic-package

Installs the Linux `amd64` or `arm64` build chosen from `uname -m`, so it runs
on `ubuntu-*` and `ubuntu-*-arm` runners; other platforms fail with a clear
message. Each download is checked against the
`elastic-package_<version>_checksums.txt` asset of the same release, and a
missing checksums asset or a missing line for the downloaded archive is a
failure rather than a skipped check. Assets come from the release download URLs,
so no `GITHUB_TOKEN` is needed.

| Input | Default | Description |
| --- | --- | --- |
| `version` | `v0.126.4` | Release to install, with or without the leading `v`. |
| `cache` | `true` | Cache the binary with [`actions/cache`](https://github.com/actions/cache), keyed on version and runner architecture. Set to `false` on runners with no cache service. |

| Output | Description |
| --- | --- |
| `version` | Installed version, without the leading `v` (for example `0.126.4`). |
| `install-path` | Directory holding the binary, added to `PATH`. |
| `cache-hit` | `true` when the binary came from the cache. |

## Verify package version

The tag is the source of truth for what gets published, but the package version
comes from `manifest.yml`. If the two disagree the release would be
mislabelled, so this fails the job.

| Input | Default | Description |
| --- | --- | --- |
| `manifest-path` | `manifest.yml` | Path to the package manifest. |
| `tag` | `${{ github.ref_name }}` | Tag to check. |
| `tag-prefix` | `v` | Prefix stripped from the tag before comparing, so `release-1.2.0` needs `tag-prefix: release-`. Pass `''` for unprefixed tags. A tag that does not start with the prefix is an error. |

| Output | Description |
| --- | --- |
| `version` | The verified version, without the tag prefix. |

## Render package release notes

A changelog entry like:

```yaml
- version: "1.2.0"
  changes:
    - description: Add the metrics data stream
      type: enhancement
      link: https://github.com/owner/repo/pull/42
```

renders as:

```markdown
- Add the metrics data stream (`enhancement`) [#42](https://github.com/owner/repo/pull/42)

Install with **Kibana > Integrations > Upload integration**, or `elastic-package install --zip <file>`.
```

Links are shortened to `[#42]` only when they end in a number, so other links
are left out rather than rendered as bare URLs. The trailing paragraph is the
default `footer`.

| Input | Default | Description |
| --- | --- | --- |
| `changelog-path` | `changelog.yml` | Path to the package changelog. |
| `version` | *(from the tag)* | Version to render notes for. |
| `tag` | `${{ github.ref_name }}` | Tag the version is derived from. Ignored when `version` is set. |
| `tag-prefix` | `v` | Prefix stripped from the tag to get the version. Ignored when `version` is set. |
| `footer` | Kibana upload instructions | Markdown appended after the changelog body, separated by a blank line. Pass `''` to omit. |
| `output-file` | `${RUNNER_TEMP}/release-notes.md` | File to write the notes to. |
| `fail-if-missing` | `false` | Fail when the changelog has no entry for the version, instead of rendering a placeholder. |

| Output | Description |
| --- | --- |
| `notes` | The rendered markdown. |
| `notes-file` | Path to the file holding the markdown. |
| `version` | Version the notes were rendered for. |
| `found` | `true` when the changelog had an entry for the version. |

## Development

The two subpath actions need `python3`, which the hosted Ubuntu images have;
PyYAML is installed on demand. Their shared scripts live in `scripts/` and are
covered by unit tests:

```sh
python -m pip install -r requirements-dev.txt
python -m pytest
```

`.github/workflows/test.yml` runs those tests and exercises all three actions,
including the arm64 install path. Integration tests that build and publish real
packages end to end live in
[`elastic-package-workflows`](https://github.com/NateShoffner/elastic-package-workflows),
so this repository stays small enough to audit.

## License

[MIT](LICENSE)
