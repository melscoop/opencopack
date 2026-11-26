# OpenCopack analytics (visits and affiliate clicks)

Free visit and outbound-click tracking for https://opencopack.com, used by the Monday Telegram money report.

The site is on GitHub Pages and the Cloudflare DNS records are DNS-only (gray cloud), so edge analytics and automatic snippet injection do not apply. Measurement is the JavaScript Web Analytics beacon, plus internal `/go/` hop pages for affiliate clicks.

## What is measured

- **Visits and pageviews** for the whole site, from the Cloudflare Web Analytics beacon on every page.
- **Affiliate clicks** as pageviews of the hop pages:
  - ReciPal: https://opencopack.com/go/recipal/ → `https://www.recipal.com?via=melanie`
  - ShipBob: https://opencopack.com/go/shipbob/ → `https://partnerwith.shipbob.com/z8mh90veiuzz`
- Guides link to those `/go/` paths with `rel="sponsored noopener"`. The hop page is `noindex`, is omitted from the sitemap, and is disallowed in `robots.txt`. It meta-refreshes after 1 second (so the beacon can fire) and has a disclosed fallback link with `rel="sponsored noopener"`.

Search Console remains the fallback for impressions and clicks if Web Analytics is unavailable, and should stay in the Monday report either way.

## Cloudflare identifiers

- Account: `2650b65f004f1023c6bf8c5cc836c72a`
- Zone (opencopack.com only; do not touch other zones or workers): `5d4334dada6c341e6bb18e552d84386c`
- Web Analytics `site_tag`: `d474a6598ca244c7936f3a74299f48fd`
- Beacon token: public, set as `CF_WEB_ANALYTICS_TOKEN` in `/workspace/mogul/site/scripts/build.py` (override with the env var of the same name). It is not a password.

Dashboard: https://dash.cloudflare.com/2650b65f004f1023c6bf8c5cc836c72a/web-analytics

## Query for the last 7 days (Monday report)

Use the GraphQL Analytics API. The token or connector session needs **Account Analytics Read**. Prefer the `user-Cloudflare` connector `execute` / `cloudflare.request` so no long-lived token is stored on the box.

`count` is pageviews. `sum.visits` is visits (pageviews whose document referrer is a different host — for a `/go/` hop, a click from an OpenCopack guide may count as a pageview but not always as a visit). For affiliate clicks, use **pageviews (`count`) of `/go/recipal/` and `/go/shipbob/`**, not visits. Also request `avg.sampleInterval`: values above 1 mean older days may be sampled and rounded.

`bot: 0` drops known bots. Confirm `requestPath` values against a live response the first time (they should be `/go/recipal/` and `/go/shipbob/`; if empty, retry without a trailing slash).

```graphql
query ($account: String!, $site: String!, $start: Date!, $end: Date!) {
  viewer {
    accounts(filter: { accountTag: $account }) {
      totals: rumPageloadEventsAdaptiveGroups(
        limit: 1
        filter: {
          siteTag: $site
          date_geq: $start
          date_leq: $end
          bot: 0
        }
      ) {
        count
        sum { visits }
        avg { sampleInterval }
      }
      clicks: rumPageloadEventsAdaptiveGroups(
        limit: 10
        filter: {
          siteTag: $site
          date_geq: $start
          date_leq: $end
          bot: 0
          requestPath_in: ["/go/recipal/", "/go/shipbob/"]
        }
      ) {
        count
        sum { visits }
        avg { sampleInterval }
        dimensions { requestPath }
      }
    }
  }
}
```

Variables (America/New_York calendar dates; for a Monday report, `start` is the previous Monday and `end` is Sunday):

```json
{
  "account": "2650b65f004f1023c6bf8c5cc836c72a",
  "site": "d474a6598ca244c7936f3a74299f48fd",
  "start": "2026-11-23",
  "end": "2026-11-29"
}
```

Via the Cloudflare connector (do not log the raw token or other sites). POST to `/graphql` relative to the API root, or `https://api.cloudflare.com/client/v4/graphql`:

```js
async () => {
  const start = "YYYY-MM-DD";
  const end = "YYYY-MM-DD";
  const site = "d474a6598ca244c7936f3a74299f48fd";
  const query = `query ($account: String!, $site: String!, $start: Date!, $end: Date!) {
    viewer {
      accounts(filter: { accountTag: $account }) {
        totals: rumPageloadEventsAdaptiveGroups(
          limit: 1
          filter: { siteTag: $site, date_geq: $start, date_leq: $end, bot: 0 }
        ) { count sum { visits } avg { sampleInterval } }
        clicks: rumPageloadEventsAdaptiveGroups(
          limit: 10
          filter: {
            siteTag: $site, date_geq: $start, date_leq: $end, bot: 0
            requestPath_in: ["/go/recipal/", "/go/shipbob/"]
          }
        ) { count sum { visits } avg { sampleInterval } dimensions { requestPath } }
      }
    }
  }`;
  return cloudflare.request({
    method: "POST",
    path: "/graphql",
    body: {
      query,
      variables: {
        account: "2650b65f004f1023c6bf8c5cc836c72a",
        site,
        start,
        end,
      },
    },
  });
}
```

Report:

- Site visits: `totals.sum.visits`
- Site pageviews: `totals.count`
- ReciPal clicks: `clicks` row where `requestPath` is `/go/recipal/` → `count`
- ShipBob clicks: same for `/go/shipbob/`
- If `avg.sampleInterval` is not 1, say the figures are sampled estimates
- Keep Search Console impressions and clicks in the same report
- Earnings still come from partner dashboards (ReciPal, ShipBob), not from these counts

If the GraphQL call returns 403, or no Web Analytics site exists, use Search Console only and note that visit and `/go/` click counts are unavailable.

## Scope

On Cloudflare, touch only the opencopack.com Web Analytics site and, if needed, the opencopack.com zone (`5d4334dada6c341e6bb18e552d84386c`). Do not list, edit, or create other Web Analytics sites, zones, or workers.
