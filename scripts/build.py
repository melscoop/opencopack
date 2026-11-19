#!/usr/bin/env python3
"""Build the OpenCopack static site into dist/."""
from __future__ import annotations

import json
import shutil
from collections import defaultdict
from datetime import date
from pathlib import Path
import os

from jinja2 import Environment, FileSystemLoader, select_autoescape

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
TODAY = date.today().isoformat()
# Production canonical / sitemap origin. Override with SITE_URL= for a local-only build.
SITE_URL = os.environ.get("SITE_URL", "https://melscoop.github.io/opencopack")
REPO_URL = os.environ.get("REPO_URL", "https://github.com/melscoop/opencopack")
CLAIM_ISSUE_URL = f"{REPO_URL.rstrip('/')}/issues/new?template=claim.yml"

CATEGORY_NAMES = {
    "sauces": "Sauces & condiments",
    "beverages": "Beverages",
    "snacks": "Snacks & confections",
    "baked-goods": "Baked goods",
    "dry-mixes": "Dry mixes, spices & grains",
    "supplements": "Supplements",
    "jams-and-spreads": "Jams, honey & spreads",
    "dairy": "Dairy",
    "meat": "Meat",
    "frozen": "Frozen",
    "other": "Other / uncategorized",
}
CATEGORY_LEDES = {
    "sauces": "Plants whose public sources mention sauces, dressings, salsas, marinades, mustards, or other condiments.",
    "beverages": "Plants whose public sources mention beverage bottling, canning, coffee, kombucha, juices, spirits, or drink mixes.",
    "snacks": "Plants whose public sources mention snacks, candy, bars, granola, chips, gummies, or similar.",
    "baked-goods": "Plants whose public sources mention bakery or baked goods.",
    "dry-mixes": "Plants whose public sources mention dry mixes, spices, blends, flours, or grains.",
    "supplements": "Plants whose public sources mention dietary supplements or related formats such as capsules, stick packs, or gummies.",
    "jams-and-spreads": "Plants whose public sources mention jams, jellies, honey, syrups, or nut butters.",
    "dairy": "Plants whose public sources mention dairy, cheese, or similar.",
    "meat": "Plants whose public sources mention meat products, sausage, or jerky. Confirm inspection status with the plant.",
    "frozen": "Plants whose public sources mention frozen foods.",
    "other": "Plants we could categorize only loosely from the published text.",
}

# Always publish hubs for Co-Packer Match gap states, even at zero listings.
GAP_STATES = ["OK", "RI", "SD", "WY", "DC"]
STATE_NAMES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas",
    "CA": "California", "CO": "Colorado", "CT": "Connecticut", "DC": "District of Columbia",
    "DE": "Delaware", "FL": "Florida", "GA": "Georgia", "HI": "Hawaii",
    "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine",
    "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska",
    "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico",
    "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island",
    "SC": "South Carolina", "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas",
    "UT": "Utah", "VT": "Vermont", "VA": "Virginia", "WA": "Washington",
    "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming",
}


def load_data():
    raw = json.loads((ROOT / "data" / "copackers.json").read_text())
    guides = []
    gdir = ROOT / "src" / "guides"
    if gdir.exists():
        for path in sorted(gdir.glob("*.json")):
            guides.append(json.loads(path.read_text()))
    guides.sort(key=lambda g: g.get("date", ""), reverse=True)
    return raw, guides


def env():
    return Environment(
        loader=FileSystemLoader(str(ROOT / "templates")),
        autoescape=select_autoescape(["html"]),
    )


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    if not text.endswith("\n"):
        path.write_text(text + "\n")


def canon(path: str) -> str:
    if SITE_URL:
        return SITE_URL.rstrip("/") + "/" + path.lstrip("/")
    return "/" + path.lstrip("/")


def root_prefix(depth: int) -> str:
    return "" if depth == 0 else "../" * depth


def dumps(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def build() -> None:
    data, guides = load_data()
    listings = data["listings"]
    generated = data.get("generated", TODAY)
    jinja = env()

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir()
    shutil.copytree(ROOT / "static", DIST / "static")

    by_state = defaultdict(list)
    by_cat = defaultdict(list)
    certs = set()
    for p in listings:
        by_state[p["state_abbr"]].append(p)
        for c in p["categories"]:
            by_cat[c].append(p)
        certs.update(p["certifications"])

    # Include empty gap-state hubs
    state_abbrs = sorted(set(by_state) | set(GAP_STATES), key=lambda a: STATE_NAMES.get(a, a))
    states_meta = [
        {"abbr": a, "name": STATE_NAMES.get(a, a), "count": len(by_state.get(a, []))}
        for a in state_abbrs
    ]
    categories_meta = [
        {"slug": slug, "name": CATEGORY_NAMES[slug], "count": len(by_cat.get(slug, []))}
        for slug in CATEGORY_NAMES
        if slug in by_cat or slug != "other"
    ]
    # only include cats that exist or are core
    categories_meta = [c for c in categories_meta if c["count"] or c["slug"] in ("sauces", "beverages", "snacks", "dry-mixes")]

    # HOME
    item_list = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "OpenCopack food and beverage co-packer directory",
        "description": "Publicly sourced listings of U.S. food and beverage co-packers.",
        "numberOfItems": len(listings),
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": i + 1,
                "url": canon(f"plants/{p['slug']}/"),
                "name": p["name"],
            }
            for i, p in enumerate(listings[:50])
        ],
    }
    html = jinja.get_template("home.html").render(
        title="OpenCopack — an open directory of food and beverage co-packers",
        description="Find U.S. food and beverage co-packers by process, state, certifications, and published minimums. Compiled from official lists and company websites.",
        canonical=canon(""),
        nav="home",
        root=root_prefix(0),
        listings=listings,
        states=states_meta,
        categories=categories_meta,
        certifications=sorted(certs),
        category_names=CATEGORY_NAMES,
        state_count=len(by_state),
        moq_count=sum(1 for p in listings if p["moq_published"]),
        generated=generated,
        jsonld=dumps({"@context": "https://schema.org", "@graph": [
            {"@type": "WebSite", "name": "OpenCopack", "url": canon(""), "description": "Open directory of U.S. food and beverage co-packers."},
            item_list,
        ]}),
    )
    write(DIST / "index.html", html)

    # PLANTS
    for p in listings:
        address = None
        if p["city"] or p["address"]:
            address = {
                "@type": "PostalAddress",
                "streetAddress": p["address"] or None,
                "addressLocality": p["city"] or None,
                "addressRegion": p["state_abbr"],
                "postalCode": p["zip"] or None,
                "addressCountry": "US",
            }
            address = {k: v for k, v in address.items() if v}
        ld = {
            "@context": "https://schema.org",
            "@type": "LocalBusiness",
            "name": p["name"],
            "url": p["website"] or canon(f"plants/{p['slug']}/"),
            "address": address,
            "telephone": p["phone"] or None,
            "email": p["email"] or None,
            "description": p["product_types"] or p["notes"] or None,
        }
        ld = {k: v for k, v in ld.items() if v}
        page = jinja.get_template("plant.html").render(
            title=f"{p['name']} in {p['city']}, {p['state_abbr']} — OpenCopack",
            description=(p["product_types"] or f"Public listing for {p['name']}, a food business in {p['city']}, {p['state']}.")[:160],
            canonical=canon(f"plants/{p['slug']}/"),
            nav="home",
            root=root_prefix(2),
            p=p,
            category_names=CATEGORY_NAMES,
            jsonld=dumps(ld),
        )
        write(DIST / "plants" / p["slug"] / "index.html", page)

    # STATE HUBS
    for abbr in state_abbrs:
        plants = by_state.get(abbr, [])
        name = STATE_NAMES.get(abbr, abbr)
        lede = (
            f"Co-packers compiled from public sources in {name}."
            if plants else
            f"We have not yet verified a plant in {name} that publicly offers co-packing or private-label contract manufacturing. If you run one, please claim a listing and point us to the page on your site that says so."
        )
        if abbr in GAP_STATES and plants:
            lede += " This is one of the states we prioritized because a competing public directory had little or no coverage here."
        ld = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"Food co-packers in {name}",
            "numberOfItems": len(plants),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": canon(f"plants/{p['slug']}/"), "name": p["name"]}
                for i, p in enumerate(plants)
            ],
        }
        page = jinja.get_template("hub.html").render(
            title=f"Food co-packers in {name} — OpenCopack",
            description=f"Publicly sourced food and beverage co-packer listings in {name}. {len(plants)} verified in this release.",
            canonical=canon(f"states/{abbr.lower()}/"),
            nav="states",
            root=root_prefix(2),
            kind="states",
            kind_label="States",
            heading=f"Co-packers in {name}",
            lede=lede,
            listings=plants,
            category_names=CATEGORY_NAMES,
            jsonld=dumps(ld),
        )
        write(DIST / "states" / abbr.lower() / "index.html", page)

    state_index = jinja.get_template("collection.html").render(
        title="Co-packers by state — OpenCopack",
        description="Browse verified food and beverage co-packer listings by U.S. state.",
        canonical=canon("states/"),
        nav="states",
        root=root_prefix(1),
        kicker="Browse",
        heading="Co-packers by state",
        lede="This seed is strongest in Colorado, Minnesota, and Utah, where official agriculture departments publish directories. We also prioritized Oklahoma, Rhode Island, and South Dakota. Wyoming and Washington, D.C. hubs are up even though we have not yet verified a plant there.",
        items=[
            {"name": s["name"], "count": s["count"], "href": f"{root_prefix(1)}states/{s['abbr'].lower()}/",
             "note": "Priority gap state" if s["abbr"] in GAP_STATES else ""}
            for s in states_meta
        ],
        jsonld=dumps({"@context": "https://schema.org", "@type": "ItemList", "name": "Co-packers by state",
                      "itemListElement": [{"@type": "ListItem", "position": i+1, "name": s["name"], "url": canon(f"states/{s['abbr'].lower()}/")} for i, s in enumerate(states_meta)]}),
    )
    write(DIST / "states" / "index.html", state_index)

    # PROCESS HUBS
    for cat in categories_meta:
        plants = by_cat.get(cat["slug"], [])
        ld = {
            "@context": "https://schema.org",
            "@type": "ItemList",
            "name": f"{cat['name']} co-packers",
            "numberOfItems": len(plants),
            "itemListElement": [
                {"@type": "ListItem", "position": i + 1, "url": canon(f"plants/{p['slug']}/"), "name": p["name"]}
                for i, p in enumerate(plants)
            ],
        }
        page = jinja.get_template("hub.html").render(
            title=f"{cat['name']} co-packers — OpenCopack",
            description=CATEGORY_LEDES.get(cat["slug"], "")[:160],
            canonical=canon(f"processes/{cat['slug']}/"),
            nav="processes",
            root=root_prefix(2),
            kind="processes",
            kind_label="Processes",
            heading=f"{cat['name']} co-packers",
            lede=CATEGORY_LEDES.get(cat["slug"], ""),
            listings=plants,
            category_names=CATEGORY_NAMES,
            jsonld=dumps(ld),
        )
        write(DIST / "processes" / cat["slug"] / "index.html", page)

    proc_index = jinja.get_template("collection.html").render(
        title="Co-packers by process — OpenCopack",
        description="Browse co-packers by sauces, beverages, snacks, dry mixes, and other process categories inferred from public sources.",
        canonical=canon("processes/"),
        nav="processes",
        root=root_prefix(1),
        kicker="Browse",
        heading="Co-packers by process",
        lede="Categories are inferred only from words the source actually published (for example, “salsa” or “beverage bottling”). They are a starting filter, not a certified capability list.",
        items=[{"name": c["name"], "count": c["count"], "href": f"{root_prefix(1)}processes/{c['slug']}/"} for c in categories_meta],
        jsonld=dumps({"@context": "https://schema.org", "@type": "ItemList", "name": "Co-packers by process",
                      "itemListElement": [{"@type": "ListItem", "position": i+1, "name": c["name"], "url": canon(f"processes/{c['slug']}/")} for i, c in enumerate(categories_meta)]}),
    )
    write(DIST / "processes" / "index.html", proc_index)

    # GUIDES
    for g in guides:
        ld = {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": g["title"],
            "dateModified": g.get("updated") or g.get("date"),
            "datePublished": g.get("date"),
            "author": {"@type": "Organization", "name": "OpenCopack"},
            "description": g.get("description"),
        }
        page = jinja.get_template("guide.html").render(
            title=f"{g['title']} — OpenCopack",
            description=g.get("description") or g["title"],
            canonical=canon(f"guides/{g['slug']}/"),
            nav="guides",
            root=root_prefix(2),
            guide=g,
            og_type="article",
            jsonld=dumps(ld),
        )
        write(DIST / "guides" / g["slug"] / "index.html", page)

    guides_index = jinja.get_template("collection.html").render(
        title="Guides — OpenCopack",
        description="Practical, sourced notes on finding a co-packer, reading minimums, and briefing a plant.",
        canonical=canon("guides/"),
        nav="guides",
        root=root_prefix(1),
        kicker="Learn",
        heading="Guides",
        lede="Short pages meant to be useful before you start calling plants. We will add one new useful page at a time.",
        items=[{"name": g["title"], "count": 1, "href": f"{root_prefix(1)}guides/{g['slug']}/", "note": g.get("kicker", "Guide")} for g in guides],
    )
    write(DIST / "guides" / "index.html", guides_index)

    # ABOUT, CLAIM, SOURCES
    about_body = f"""
    <p class="kicker">About</p>
    <h1>About OpenCopack</h1>
    <p>OpenCopack is a small, public directory of U.S. food and beverage co-packers — plants that manufacture and package a recipe for another brand. It is built as a static site so it can be hosted on a free tier, and it is designed so one useful page can be added at a time.</p>
    <p>The working principle is narrow: only publish what a public source already said, and show the source. We do not invent companies, minimum order quantities, certifications, or contact details. If a plant has not published a minimum, the listing says so.</p>
    <h2>What “verified” means here</h2>
    <p>It means we retrieved a public page — usually an official state agriculture directory or the company’s own site — and copied only what that page stated. It does not mean we toured the plant, confirmed open capacity, or tasted the product.</p>
    <h2>This first release</h2>
    <p>The seed directory was compiled on {generated} from the Colorado Department of Agriculture Co-Pack Directory, the Utah Department of Agriculture and Food Co-Packer Directory, a curated subset of the Minnesota Department of Agriculture Co-Packer Directory, and company websites for plants in Oklahoma, Rhode Island, and South Dakota. Wyoming and Washington, D.C. remain empty because we could not verify a public co-packing offer there in this pass.</p>
    <p>OpenCopack is not affiliated with Co-Packer Match, PartnerSlate, Specialty Food Co-Packers, or any listed company.</p>
    """
    write(DIST / "about" / "index.html", jinja.get_template("simple.html").render(
        title="About OpenCopack",
        description="How OpenCopack is compiled and what a listing does and does not mean.",
        canonical=canon("about/"),
        nav="about",
        root=root_prefix(1),
        body=about_body,
    ))

    claim_body = f"""
    <p class="kicker">Listings</p>
    <h1>Add or claim a plant</h1>
    <p>If you operate a licensed food plant that does contract manufacturing or private-label packing, you can ask to be listed or to correct an existing page. We will only publish capabilities, minimums, certifications, and contacts that already appear on a public page or that you send us in writing to post.</p>
    <p>For now, open a GitHub issue on the <a href="{REPO_URL}">OpenCopack repository</a> with the details below. Nothing is billed, and there is no paid placement in this version of the site.</p>
    <p><a class="btn" href="{CLAIM_ISSUE_URL}">Open a GitHub issue to add or claim a plant</a></p>
    <h2>Please include</h2>
    <ul>
      <li>Plant name</li>
      <li>City and state</li>
      <li>A website URL that states you offer co-packing or private-label packing</li>
      <li>Your name and role</li>
      <li>What we should add or correct (published minimum, processes, certifications, address, or a new listing)</li>
    </ul>
    <p class="note">We may ask you to point us to a public page before a change goes live. Do not send passwords, payment details, or other sensitive credentials in the issue.</p>
    """
    write(DIST / "claim" / "index.html", jinja.get_template("simple.html").render(
        title="Add or claim a plant — OpenCopack",
        description="Ask to add or correct a co-packer listing. We only publish facts that a public source or the plant confirms.",
        canonical=canon("claim/"),
        nav="claim",
        root=root_prefix(1),
        body=claim_body,
    ))

    sources_body = f"""
    <p class="kicker">Methodology</p>
    <h1>Sources and disclaimer</h1>
    <p>Every plant page names the public source we used and the date we retrieved it. The {len(listings)} listings in this build come from:</p>
    <ul>
      <li><a href="https://ag.colorado.gov/colorado-co-pack-directory">Colorado Department of Agriculture Co-Pack Directory</a> (Google Sheet linked from that page), retrieved {generated}. We included rows marked “Co Packer” that had a city plus published product types or a minimum. Shared kitchens were left out.</li>
      <li><a href="https://ag.utah.gov/marketing-and-economic-development/supply-chain-support/co-packers/">Utah Department of Agriculture and Food Co-Packer Directory</a>, retrieved {generated}. The official table did not include business names; we added names only after reading them on the company’s own website. Two official rows were omitted because the website did not load or listed fulfillment only.</li>
      <li><a href="https://www.mda.state.mn.us/minnesota-co-packer-directory">Minnesota Department of Agriculture Co-Packer Directory</a>, retrieved {generated}. This is a curated subset (sauces, beverages, snacks, dry mixes, and plants that published a minimum), not the entire MDA list.</li>
      <li>Company websites for plants in Oklahoma, Rhode Island, and South Dakota, each cited on the plant page, retrieved {generated}.</li>
    </ul>
    <h2>What we will not do</h2>
    <ul>
      <li>Invent a company, address, phone number, email, minimum, certification, or process.</li>
      <li>Treat “organic handler” or a USDA inspection listing alone as proof the company offers co-packing.</li>
      <li>Endorse a plant or guarantee open capacity.</li>
    </ul>
    <h2>Disclaimer</h2>
    <p>OpenCopack is an informational directory. Listings can go stale the day after we copy them. Food safety, labeling, cottage-food rules, and inspection requirements vary by product and state. Talk to the plant and, where required, a process authority before you produce anything. Links to company sites are provided for verification and are not paid placements in this release.</p>
    """
    write(DIST / "sources" / "index.html", jinja.get_template("simple.html").render(
        title="Sources and disclaimer — OpenCopack",
        description="How OpenCopack listings are compiled, which official directories were used, and what we will not invent.",
        canonical=canon("sources/"),
        nav="about",
        root=root_prefix(1),
        body=sources_body,
    ))

    # robots + sitemap
    write(DIST / "robots.txt", f"User-agent: *\nAllow: /\nSitemap: {canon('sitemap.xml')}\n")
    (DIST / ".nojekyll").write_text("")
    urls = [""]
    urls += [f"plants/{p['slug']}/" for p in listings]
    urls += ["states/", "processes/", "guides/", "about/", "claim/", "sources/"]
    urls += [f"states/{a.lower()}/" for a in state_abbrs]
    urls += [f"processes/{c['slug']}/" for c in categories_meta]
    urls += [f"guides/{g['slug']}/" for g in guides]
    sm = ['<?xml version="1.0" encoding="UTF-8"?>', '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']
    for u in urls:
        sm.append(f"  <url><loc>{canon(u)}</loc><lastmod>{TODAY}</lastmod></url>")
    sm.append("</urlset>")
    write(DIST / "sitemap.xml", "\n".join(sm) + "\n")

    # copy data for transparency
    shutil.copy(ROOT / "data" / "copackers.json", DIST / "copackers.json")

    published_guides = [g["slug"] for g in guides]
    (ROOT / "logs").mkdir(exist_ok=True)
    print(f"Built {len(list(DIST.rglob('index.html')))} HTML pages into {DIST}")
    print(f"Listings: {len(listings)}; guides: {published_guides}; states: {len(state_abbrs)}")


if __name__ == "__main__":
    build()
