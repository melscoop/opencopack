# Deploying OpenCopack

- Live site: https://melscoop.github.io/opencopack/
- Repository: https://github.com/melscoop/opencopack
- GitHub account used: `melscoop`, via the box `gh` CLI (`gh auth setup-git` for the local credential helper)

Pages is enabled on this repo with `build_type=workflow`. A push to `main` runs `.github/workflows/pages.yml`, which rebuilds the site with `SITE_URL=https://melscoop.github.io/opencopack` and deploys it. The same workflow also publishes an orphan `gh-pages` branch from `dist/` (including `.nojekyll`) as a fallback. Prefer the Actions path.

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
- `dist/**` — full rebuild (especially `guides/<slug>/index.html`, `guides/index.html`, `sitemap.xml`, and any index that lists guides). Do not commit `dist/` (gitignored); Actions rebuilds it.
- `logs/nightly.log` — local only; do not commit (gitignored)

If you later add listings, `data/copackers.json` also changes. Run `scripts/compile_data.py` only when you have new sourced data, then `scripts/build.py`.

## How a later run publishes (git push via gh)

Stay in `/workspace/mogul/site`. This directory is already a git checkout of `melscoop/opencopack` on `main`. Use the box `gh` login (`melscoop`); `gh auth setup-git` is enough if HTTPS pushes ask for credentials. Do not create a new repo, and do not change other repositories or account settings.

```sh
cd /workspace/mogul/site
./nightly.sh
git add data/queue.json src/guides/<slug>.json
git status   # confirm only the intended source files are staged; no dist/, .venv/, or logs/
git commit -m "Publish guide: <title>"
git push origin main
gh run watch --repo melscoop/opencopack
```

A push to `main` triggers the Pages workflow. You do not need to upload `dist/` for the live site when that run succeeds.

If the Actions deploy fails, the `gh-pages` branch is the fallback (the workflow updates it when it can). Pages can be pointed at `gh-pages` / root for this repo only, for example:

```sh
gh api -X PUT repos/melscoop/opencopack/pages -f build_type=legacy -f source[branch]=gh-pages -f source[path]=/
```

Prefer leaving `build_type=workflow` unless that path is broken.

Then verify these return HTTP 200 and contain expected titles:

- https://melscoop.github.io/opencopack/
- https://melscoop.github.io/opencopack/guides/<slug>/
- one listing URL under https://melscoop.github.io/opencopack/plants/

If a later deploy fails because Pages was turned off, turn it back on for this repo only:

```sh
gh api -X POST repos/melscoop/opencopack/pages -f build_type=workflow
```

(Use `PUT` with the same field if the Pages site already exists.)
