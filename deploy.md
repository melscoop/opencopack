# Deploying OpenCopack

- Live site: https://melscoop.github.io/opencopack/
- Repository: https://github.com/melscoop/opencopack
- GitHub account used: `melscoop` (via the `user-GitHub-xai` connector)

## What a nightly run changes locally

From `/workspace/mogul/site`, run `./nightly.sh`. That script is not scheduled; a later routine should call it and then deploy.

Each run:

1. Takes the next item in `data/queue.json` whose `status` is `queued`.
2. Writes the pre-written guide to `src/guides/<slug>.json` and marks the queue item `published`.
3. Rebuilds the static site with `scripts/build.py` (default `SITE_URL` is `https://melscoop.github.io/opencopack`).
4. Appends a line to `logs/nightly.log`.

It does not invent company facts, and it does not push to GitHub by itself.

### Files that change

- `data/queue.json` — item `status` and `published_on`
- `src/guides/<slug>.json` — new guide source
- `dist/**` — full rebuild (especially `guides/<slug>/index.html`, `guides/index.html`, `sitemap.xml`, and any index that lists guides)
- `logs/nightly.log` — local only; do not commit (gitignored)

If you later add listings, `data/copackers.json` and many plant/hub pages under `dist/` also change. Run `scripts/compile_data.py` only when you have new sourced data, then `scripts/build.py`.

## How a later run publishes through the connector

Use the `user-GitHub-xai` MCP tools as user `melscoop`. Do not create a new repo.

1. **Push the new source to `main`** with `push_files`:
   - `owner`: `melscoop`
   - `repo`: `opencopack`
   - `branch`: `main`
   - `files`: at least `data/queue.json` and `src/guides/<slug>.json` (path and full text content of each)
   - `message`: e.g. `Publish guide: <title>`

   For a one-file fix you can use `create_or_update_file` instead, but updates need the current blob `sha` from `get_file_contents`.

2. **Let GitHub Actions deploy Pages.** A push to `main` runs `.github/workflows/pages.yml`, which rebuilds with `SITE_URL=https://melscoop.github.io/opencopack` and deploys the new `dist/`. You do not need to upload `dist/` for the live site when that workflow succeeds.

3. **Optional fallback:** the same workflow also publishes an orphan `gh-pages` branch from `dist/` (including `.nojekyll`). If Pages is ever pointed at that branch (root) instead of GitHub Actions, you can also `push_files` to `branch=gh-pages` with the rebuilt site files at the branch root (`index.html`, `guides/<slug>/index.html`, `sitemap.xml`, `.nojekyll`, and so on). Prefer the Actions path.

4. **Verify** with curl that these return HTTP 200 and contain expected titles:
   - https://melscoop.github.io/opencopack/
   - https://melscoop.github.io/opencopack/guides/<slug>/
   - one listing URL under https://melscoop.github.io/opencopack/plants/

There is no GitHub Pages enable/update tool in this connector. After the first successful Actions deploy, Pages should stay on with source “GitHub Actions.” If a later deploy fails because Pages was turned off, it has to be turned back on in the repository Pages settings (source: GitHub Actions, or branch `gh-pages` / root).

## Status as of 2026-11-19 (Eastern Time)

The public `melscoop/opencopack` repository does not exist yet. `create_repository` on the `user-GitHub-xai` connector returned `403 Resource not accessible by integration` for the personal account. The connector can read public `melscoop` repos and can see the `melscoop-test` organization, but this project should go on `melscoop/opencopack` so Pages is `https://melscoop.github.io/opencopack/`.

Once that empty public repo exists (and the connector can write to it), push the source from `/workspace/mogul/site` to `main` as described above, excluding `dist/` and `.venv/`. The workflow in `.github/workflows/pages.yml` builds and deploys Pages. The connector has no Pages-enable tool; the workflow tries `POST /repos/{owner}/{repo}/pages` with `build_type=workflow`, and if that fails Pages must be turned on in the repo settings (source: GitHub Actions, or branch `gh-pages` / root).
