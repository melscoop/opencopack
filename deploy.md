# Deploying OpenCopack

- Live site: https://opencopack.com/
- www: https://www.opencopack.com/ (CNAME to `melscoop.github.io`)
- Previous GitHub Pages URL: https://melscoop.github.io/opencopack/ (GitHub usually redirects this to the custom domain once Pages is configured)
- Repository: https://github.com/melscoop/opencopack
- GitHub account used: `melscoop`, via the box `gh` CLI (`gh auth setup-git` for the local credential helper)
- DNS: Cloudflare zone `opencopack.com`. Apex A/AAAA records point at GitHub Pages IPs and are DNS-only (not proxied) so GitHub can issue the HTTPS certificate. `www` is a DNS-only CNAME to `melscoop.github.io`.

Pages is enabled on this repo with `build_type=workflow` and custom domain `opencopack.com`. A push to `main` runs `.github/workflows/pages.yml`, which rebuilds the site with `SITE_URL=https://opencopack.com` and deploys it. The build also writes a `CNAME` file (`opencopack.com`) and `.nojekyll` into `dist/`. The same workflow also publishes an orphan `gh-pages` branch from `dist/` as a fallback. Prefer the Actions path.

The default `SITE_URL` in `scripts/build.py` is `https://opencopack.com`, so a local `./nightly.sh` or `scripts/build.py` run (with no `SITE_URL` override) produces the same canonicals and sitemap as production.

## What a nightly run changes locally

From `/workspace/mogul/site`, run `./nightly.sh`. That script is not scheduled; a later routine should call it and then deploy.

Each run:

1. Takes the next item in `data/queue.json` whose `status` is `queued`.
2. Writes the pre-written guide to `src/guides/<slug>.json` and marks the queue item `published`.
3. Rebuilds the static site with `scripts/build.py` (default `SITE_URL` is `https://opencopack.com`).
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
gh api -X PUT repos/melscoop/opencopack/pages -f build_type=legacy -f source[branch]=gh-pages -f source[path]=/ -f cname='opencopack.com'
```

Prefer leaving `build_type=workflow` unless that path is broken.

Then verify these return HTTP 200 and contain expected titles:

- https://opencopack.com/
- https://opencopack.com/guides/<slug>/
- one listing URL under https://opencopack.com/plants/

If a later deploy fails because Pages was turned off, turn it back on for this repo only, keeping the custom domain:

```sh
gh api -X POST repos/melscoop/opencopack/pages -f build_type=workflow -f cname='opencopack.com'
```

(Use `PUT` with the same fields if the Pages site already exists.) Once GitHub has issued the custom-domain certificate, keep HTTPS enforced:

```sh
gh api -X PUT repos/melscoop/opencopack/pages -f build_type=workflow -f cname='opencopack.com' -F https_enforced=true
```

## Analytics

Visit and affiliate-click tracking is documented in `/workspace/mogul/analytics.md` (a copy of the same notes lives next to this file as `analytics.md` once published).

The Cloudflare Web Analytics beacon is added to `templates/base.html` when `CF_WEB_ANALYTICS_TOKEN` is set in `scripts/build.py`. Affiliate links go through `/go/recipal/` and `/go/shipbob/`, which meta-refresh to the partner URLs after one second so those pageviews can be counted as clicks. Those paths are noindex, omitted from the sitemap, and disallowed in `robots.txt`.

The Monday money report should query `rumPageloadEventsAdaptiveGroups` for the last 7 days: site `sum.visits` / `count`, plus `count` for `requestPath` `/go/recipal/` and `/go/shipbob/`, with `bot: 0`. Prefer the `user-Cloudflare` connector. Search Console remains the fallback if that API is unavailable. See `/workspace/mogul/analytics.md` for the full GraphQL query.
