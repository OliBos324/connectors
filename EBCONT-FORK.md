# EBCONT fork of elastic/connectors

Fork of [elastic/connectors](https://github.com/elastic/connectors), based on tag `v8.17.1`
(branch `ebcont/8.17`).

## What is different

The Confluence connector stores page content a second time as **Markdown** in the new field
`body_markdown`, so that tables, headings and lists survive indexing. `body` (plain text) is
unchanged.

| File | Change |
| --- | --- |
| `connectors/sources/confluence_markdown.py` | New: converts Confluence storage format to Markdown |
| `connectors/sources/confluence.py` | Adds `body_markdown` to pages/blog posts and search results, removes it for attachments |
| `requirements/framework.txt` | Adds `markdownify` |
| `tests/sources/test_confluence_markdown.py` | New tests for the converter |
| `tests/sources/test_confluence.py` | Expected documents include `body_markdown` |
| `.github/workflows/ebcont-build-image.yml` | Tests and builds the image, pushes it to ghcr.io |
| `Dockerfile.ebcont` | Image build on a public base image |

## Conversion rules

- Tables become Markdown tables; several values in one cell (lists, line breaks) are joined with `, `.
  Tables without a header row use their first row as header.
- `code`/`noformat` macros become code blocks, `info`/`note`/`warning`/`tip`/`panel` become quotes.
- `jira` macros become `Jira: <KEY>`, links to pages keep their text or the page title.
- Macro parameters are dropped. User mentions (`@name`) only contain a user id in the storage
  format and are therefore empty.
- If the conversion fails, `body_markdown` is `null` and the sync continues.

## Image

`ghcr.io/olibos324/elastic-connectors:<tag>`, built from `Dockerfile.ebcont` (public base image
`python:3.11-slim-bookworm`; the pinned wolfi base image of v8.17.1 is no longer publicly
pullable). Start command is the same as for the official image:
`/app/bin/elastic-ingest -c /config/config.yml`.

- `8.17-ebcont`: latest state of `ebcont/8.17`
- `8.17.1-ebcont.<n>`: fixed release, created by pushing the git tag `v8.17.1-ebcont.<n>`

## Before the first sync

Map the new field without indexing, otherwise the connector's dynamic templates index it with
many full-text subfields:

```
PUT <confluence-connector-index>/_mapping
{ "properties": { "body_markdown": { "type": "text", "index": false } } }
```

Then run a **full sync** so every page gets the new field.

## Updating from upstream

```
git fetch upstream --tags
git rebase <new-upstream-tag>   # on a new branch, e.g. ebcont/8.18
```

Never commit `config.yml`, API keys or internal URLs: this repository is public.
