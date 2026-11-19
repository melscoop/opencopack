# OpenCopack

A static directory of U.S. food and beverage co-packers. Listings are compiled from official state agriculture directories and company websites. If a source did not publish a fact, the field is left blank.

- Live site: https://melscoop.github.io/opencopack/
- Repository: https://github.com/melscoop/opencopack

To add or correct a listing, [open a GitHub issue](https://github.com/melscoop/opencopack/issues/new?template=claim.yml).

## Preview locally

From this directory, after a build:

```sh
/workspace/mogul/.venv/bin/python scripts/build.py
/workspace/mogul/.venv/bin/python -m http.server 8765 --directory dist
```

Then open http://127.0.0.1:8765/

The default `SITE_URL` is the GitHub Pages origin, so canonical tags and the sitemap point at the live site. Asset and navigation links stay relative, so a local preview still works. For fully local canonicals, run `SITE_URL= python scripts/build.py`.

## Rebuild from source data

```sh
/workspace/mogul/.venv/bin/python scripts/compile_data.py   # optional, regenerates data/copackers.json
/workspace/mogul/.venv/bin/python scripts/build.py
```

## Nightly page

```sh
./nightly.sh
```

Publishes the next queued guide, rebuilds, and logs the result. It does not deploy. See [deploy.md](deploy.md) for how a later run pushes through the GitHub connector.
