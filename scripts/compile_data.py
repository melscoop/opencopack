#!/usr/bin/env python3
"""Compile co-packer listings from official public sources.

Never invent companies, capabilities, MOQs, certifications, or contacts.
Unknown fields are left empty. Every record keeps its source URL.
"""
from __future__ import annotations

import csv
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "copackers.json"
RETRIEVED = "2026-11-19"

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
NAME_TO_ABBR = {v.lower(): k for k, v in STATE_NAMES.items()}
NAME_TO_ABBR["district of columbia"] = "DC"
NAME_TO_ABBR["washington, dc"] = "DC"
NAME_TO_ABBR["washington dc"] = "DC"

# Hub categories used on the site. A plant can appear in several.
CATEGORY_RULES = [
    ("sauces", r"sauce|dressing|salsa|condiment|marinade|pickle|relish|mustard|hot sauce|bbq|barbecue"),
    ("beverages", r"beverage|juice|bottl|coffee|kombucha|seltzer|tea|drink|spirit|cocktail|mocktail|wine|beer|kefir|frappe"),
    ("snacks", r"snack|candy|confection|granola|chip|bar\b|pretzel|trail mix|nut mix|gummi|popped|puff|jerky"),
    ("baked-goods", r"bakery|baked|bread|cookie|cake|pastry|dough"),
    ("dry-mixes", r"dry mix|bakery mix|powder|spice|seasoning|blend|flour|grain|rice|bean|lentil|cereal"),
    ("supplements", r"supplement|nutraceutical|gummi|capsule|tablet|cbd|hemp|probiotic"),
    ("jams-and-spreads", r"jam|jelly|preserv|honey|nut butter|spread|syrup|fruit filling"),
    ("dairy", r"\bdairy\b|cheese|yogurt|butter\b|cream"),
    ("meat", r"\bmeat\b|sausage|poultry|pork|beef|jerky|smokehouse"),
    ("frozen", r"frozen|ice cream|gelato"),
]

CERT_RULES = [
    ("USDA Organic", r"usda organic|\borganic certified\b|organic production certification|\borganic\b certified"),
    ("Organic", r"\borganic\b"),
    ("SQF", r"\bsqf\b"),
    ("GFSI", r"\bgfsi\b"),
    ("Kosher", r"\bkosher\b"),
    ("Halal", r"\bhalal\b"),
    ("Gluten-free", r"gluten[ -]?free"),
    ("GMP", r"\bc?gmp\b"),
    ("FDA registered", r"fda[ -]?registered"),
    ("USDA inspected", r"usda[ -]?inspect"),
    ("Nut-free", r"nut[ -]?free"),
    ("MBE", r"\bmbe\b"),
]

STARTUP_RE = re.compile(
    r"start-?ups?|small business|small-batch|small batch|short runs are welcome|"
    r"no minimum|none$|^none$|order what you need|trial runs|"
    r"specialize in small|emerging brand|exceptions can be made|"
    r"negotiable|startup-friendly|low moqs?",
    re.I,
)


def slugify(text: str) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")[:80]


def normalize_url(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return ""
    if url.startswith("www."):
        url = "https://" + url
    elif re.match(r"^[a-z0-9.-]+\.[a-z]{2,}", url, re.I) and not url.startswith("http"):
        url = "https://" + url
    return url


def infer_categories(*blobs: str) -> list[str]:
    text = " | ".join(b for b in blobs if b).lower()
    found = []
    for cat, rx in CATEGORY_RULES:
        if re.search(rx, text, re.I):
            found.append(cat)
    return found or ["other"]


def infer_certs(*blobs: str) -> list[str]:
    text = " | ".join(b for b in blobs if b)
    found = []
    seen = set()
    for label, rx in CERT_RULES:
        if re.search(rx, text, re.I) and label not in seen:
            # If we already added USDA Organic, skip generic Organic
            if label == "Organic" and "USDA Organic" in seen:
                continue
            found.append(label)
            seen.add(label)
    return found


def startup_flag(*blobs: str) -> bool:
    text = " | ".join(b for b in blobs if b)
    return bool(STARTUP_RE.search(text))


def clean_moq(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return ""
    # Do not treat vague empties as a published number
    if value.lower() in {"n/a", "na", "tbd", ".", "-"}:
        return ""
    return re.sub(r"\s+", " ", value)


def record(**kwargs) -> dict:
    name = kwargs["name"].strip()
    city = kwargs.get("city") or ""
    state_abbr = kwargs["state_abbr"]
    slug = slugify(f"{name}-{city}-{state_abbr}")
    moq = clean_moq(kwargs.get("moq") or "")
    rec = {
        "slug": slug,
        "name": name,
        "city": city.strip(),
        "state": STATE_NAMES.get(state_abbr, kwargs.get("state") or state_abbr),
        "state_abbr": state_abbr,
        "address": (kwargs.get("address") or "").strip(),
        "zip": (kwargs.get("zip") or "").strip(),
        "website": normalize_url(kwargs.get("website") or ""),
        "phone": (kwargs.get("phone") or "").strip(),
        "email": (kwargs.get("email") or "").strip(),
        "product_types": (kwargs.get("product_types") or "").strip(),
        "processes": kwargs.get("processes") or [],
        "categories": kwargs.get("categories") or infer_categories(
            kwargs.get("product_types") or "", " ".join(kwargs.get("processes") or []), kwargs.get("notes") or ""
        ),
        "certifications": kwargs.get("certifications") or infer_certs(
            kwargs.get("product_types") or "", kwargs.get("notes") or "", kwargs.get("information") or ""
        ),
        "moq": moq,
        "moq_published": bool(moq),
        "startup_friendly": bool(kwargs.get("startup_friendly")),
        "notes": (kwargs.get("notes") or "").strip(),
        "sources": kwargs["sources"],
    }
    if not rec["startup_friendly"]:
        rec["startup_friendly"] = startup_flag(moq, rec["notes"], rec["product_types"], kwargs.get("information") or "")
    return rec


def load_colorado() -> list[dict]:
    path = Path("/tmp/copack-src/co-560248172.csv")
    rows = list(csv.DictReader(path.open()))
    out = []
    source = {
        "name": "Colorado Department of Agriculture Co-Pack Directory",
        "url": "https://ag.colorado.gov/colorado-co-pack-directory",
        "retrieved": RETRIEVED,
        "dataset": "https://docs.google.com/spreadsheets/d/1r5VCrCkI6ONwWipD-_fNCDBAS4CWUdNuKODj7OSFWzk/edit",
    }
    for r in rows:
        if (r.get("Operation Type") or "").strip() != "Co Packer":
            continue
        name = (r.get("Name") or "").strip()
        city = (r.get("City") or "").strip()
        st = (r.get("State") or "CO").strip() or "CO"
        if not name or not city:
            continue
        if "kitchen share" in name.lower():
            continue
        processes = []
        info = (r.get("Information") or "").strip()
        products = (r.get("PRODUCT TYPES") or "").strip()
        moq = r.get("MINIMUM RUN") or ""
        # Skip official rows that published neither products nor a minimum;
        # they can be added later once capabilities are verified on a source page.
        if not products and not (moq or "").strip():
            continue
        notes_parts = []
        if info:
            notes_parts.append(info)
        rec = record(
            name=name,
            city=city,
            state_abbr=st,
            address=r.get("Address") or "",
            zip=r.get("Zip Code") or "",
            website=r.get("Website") or "",
            phone=r.get("Phone") or "",
            email=r.get("Email") or "",
            product_types=products,
            processes=processes,
            moq=moq,
            notes=" ".join(notes_parts),
            information=info,
            sources=[source],
        )
        rec["categories"] = infer_categories(products, info, moq)
        rec["certifications"] = infer_certs(products, info)
        rec["startup_friendly"] = startup_flag(moq, info, products)
        # Published "Updated" date from the sheet, if present
        if (r.get("Updated") or "").strip():
            rec["source_updated"] = r["Updated"].strip()
        out.append(rec)
    return out


def load_utah() -> list[dict]:
    """Utah official directory did not publish business names in the table.
    Names below were read from each company's own website on 2026-11-19.
    Listings whose websites could not be fetched are omitted.
    """
    source = {
        "name": "Utah Department of Agriculture and Food Co-Packer Directory",
        "url": "https://ag.utah.gov/marketing-and-economic-development/supply-chain-support/co-packers/",
        "retrieved": RETRIEVED,
    }
    # Official-directory fields + website-confirmed legal/trade name
    plants = [
        {
            "name": "KeyStone Co-Pack",
            "website": "https://www.keystonecopack.com/",
            "phone": "801-901-7812",
            "address": "1057 W. 700 S. Ste. 400",
            "city": "Pleasant Grove",
            "zip": "84062",
            "product_types": "Bakery Mixes / Dry Mixes, Beverages, Dietary Supplements, Skincare",
            "processes": ["Beverage bottling", "Blending", "Canning / jarring", "Labeling", "Pills / capsules", "Sticks", "Tablets", "Gusseted bags"],
            "notes": "UDAF lists these product categories and services. The company's website describes turnkey supplement manufacturing, R&D, blending, filling, and packaging.",
        },
        {
            "name": "Millcreek Cacao Roasters",
            "website": "https://www.millcreekcacao.com/",
            "phone": "801-850-1250",
            "address": "50 West Century Park Way",
            "city": "South Salt Lake",
            "zip": "84115",
            "product_types": "Bakery Mixes / Dry Mixes, Candy / Confections, Tea, Cacao Products",
            "processes": ["Blending", "Labeling", "Flow wrap - bagging - boxes"],
            "notes": "UDAF lists these product categories and services. The company's website also advertises private label.",
        },
        {
            "name": "Cpack Manufacturing",
            "website": "https://cpackmanufacturing.com/",
            "phone": "801-224-1910",
            "address": "926 N 1430 W",
            "city": "Orem",
            "zip": "84057",
            "product_types": "Dietary Supplements, Gummies",
            "processes": ["Blending", "Labeling", "Pills / capsules", "Sticks", "Tablets"],
            "notes": "UDAF lists supplement and gummy packing. The company's website describes itself as an FDA-registered, cGMP-certified nutraceutical contract manufacturer in Orem, Utah.",
            "certifications": ["FDA registered", "GMP"],
        },
        {
            "name": "Cornaby's",
            "website": "https://cornabys.com/food-co-packing-services/",
            "phone": "801-472-8365",
            "address": "1693 W American Way, #10",
            "city": "Payson",
            "zip": "84651",
            "product_types": "Candy / Confections, Dietary Supplements, Dressings / Sauces / Salsas, Flavorings / Extracts / Syrups, Fruit Spreads / Jams / Preserves, Grains / Nuts / Seeds, Sauce / Condiment, Dry mixes, Nut butters",
            "processes": ["Blending", "Canning / jarring", "Fulfillment", "Labeling", "Sticks", "Pouches"],
            "notes": "UDAF lists these categories. The company publishes a Food Co-Packing Services page covering jam and jelly co-packing and private label, among other products.",
        },
        {
            "name": "Snack Connector",
            "website": "https://www.snackconnector.com/",
            "phone": "801-259-3448",
            "address": "3622 West 1820 South",
            "city": "Salt Lake City",
            "zip": "84104",
            "product_types": "Candy / Confections, Grains / Nuts / Seeds",
            "processes": ["Blending", "Fulfillment", "Labeling", "Flavor application", "roasting", "packaging"],
            "notes": "UDAF lists confection and grain/nut packing plus roasting. The company's website describes snack contract manufacturing, co-packing, product development, and fulfillment.",
        },
        {
            "name": "CorePack Manufacturing",
            "website": "https://www.corepackmfg.com/",
            "phone": "801-598-5428",
            "address": "165 N 1330 W suite B4",
            "city": "Orem",
            "zip": "84057",
            "product_types": "Bakery Mixes / Dry Mixes, Dietary Supplements, Flavorings / Extracts / Syrups, Gels, Grains / Nuts / Seeds, Oils / extracts, Skincare, Spices",
            "processes": ["Blending", "Labeling", "Pills / capsules", "Sticks"],
            "notes": "UDAF lists these categories. The company's website advertises contract manufacturing services.",
        },
        {
            "name": "Propeller Co-Pack",
            "website": "https://propellercopack.com/",
            "phone": "801-211-5999",
            "address": "1233 W 1950 N",
            "city": "Santaquin",
            "zip": "84655",
            "product_types": "Bakery Mixes / Dry Mixes, Dietary Supplements, Grains / Nuts / Seeds, Pet Treats",
            "processes": ["Blending", "Fulfillment", "Labeling", "Sticks", "Sachets"],
            "notes": "Address and phone are as published by UDAF. The company's website also lists an office in Pleasant Grove and a Santaquin manufacturing address, and describes powder blending, pouch and stick-pack filling, and startup-friendly / low-MOQ packaging. No numeric minimum was published on the pages reviewed.",
            "startup_friendly": True,
        },
        {
            "name": "Basic Foods",
            "website": "https://www.basicfoods.net/",
            "phone": "801-399-0440",
            "address": "2714 N. 1600 W.",
            "city": "Pleasant View",
            "zip": "84404",
            "product_types": "Dressings / Sauces / Salsas, Sauce / Condiment",
            "processes": ["Blending", "Labeling"],
            "notes": "UDAF lists sauce and dressing blending. The company's website says it manufactures sauces, dressings, and condiments for restaurants, retailers, and private-label brands.",
        },
    ]
    out = []
    for p in plants:
        rec = record(
            name=p["name"],
            city=p["city"],
            state_abbr="UT",
            address=p.get("address"),
            zip=p.get("zip"),
            website=p.get("website"),
            phone=p.get("phone"),
            product_types=p.get("product_types"),
            processes=p.get("processes"),
            notes=p.get("notes"),
            startup_friendly=p.get("startup_friendly", False),
            sources=[source, {"name": f"{p['name']} website", "url": p["website"], "retrieved": RETRIEVED}],
        )
        if p.get("certifications"):
            # merge
            rec["certifications"] = list(dict.fromkeys(p["certifications"] + rec["certifications"]))
        out.append(rec)
    return out


def load_minnesota() -> list[dict]:
    """Curated subset of the Minnesota Department of Agriculture directory.

    The live MDA page is the source. A full table and many plant detail
    blocks (including published minimums) were captured from that page on
    2026-11-19. We include a subset useful to small and mid-size food
    brands (sauces, beverages, snacks, dry mixes, and plants that published
    a minimum). We do not invent contacts or MOQs; detail comes only from
    the MDA page.
    """
    source = {
        "name": "Minnesota Department of Agriculture Co-Packer Directory",
        "url": "https://www.mda.state.mn.us/minnesota-co-packer-directory",
        "retrieved": RETRIEVED,
    }
    # name, city, state_abbr, product_types, moq (only if MDA published it)
    chosen = [
        ("TWT Sauce Inc.", "Hudson", "WI", "Acidic and acidified canned foods like salsa, sauces, and marinades", "varies by product",
         "MDA: gluten-free facility focusing on acidic and acidified foods through small-batch production to support emerging small businesses. Products listed include salsa, pasta sauces, bloody mary and cocktail mixes, barbecue sauces, marinades, hot sauces, and chili sauces."),
        ("Croix Valley Foods", "Hudson", "WI", "Acidic and acidified canned foods", "100 gallons on liquid products, 150 pounds on dry blends", ""),
        ("Gourmet CoPack", "Minneapolis", "MN", "Preserves, conserves, pickles, and sauces", "1,000 units", ""),
        ("At Last! Gourmet Foods", "Minneapolis", "MN", "Soups, sauces, marinades, dips, and spreads", "1 pallet (1,200 pounds)", ""),
        ("Bare Honey & Co. Food Manufacturing", "Minneapolis", "MN", "Honey, jams/jellies, sauces, drink mixers", "", ""),
        ("Fischer's United Supply Inc.", "Minneapolis", "MN", "Sauces, dressings, marinades, salsas, dips, jams, and jellies", "500 pounds", ""),
        ("Mixly Cocktail Co.", "New Hope", "MN", "Cocktail mixers, mocktails, syrups, juices, functional beverages - glass or plastic", "To be determined on product type, packaging and formula.", ""),
        ("Kaye Family Foods", "River Falls", "WI", "Acidic and acidified canned foods like BBQ sauce, salsa, hot sauce, and bloody mary mix", "no minimums - order what you need", ""),
        ("Karlsburger Foods Inc.", "Monticello", "MN", "Sauces, spices, and dry mixes", "no minimum on stock items; 150 pounds custom seasoning or dry blends; 300 pounds on custom bases", ""),
        ("Nikola's Foods, Nikola's Bakery", "Bloomington", "MN", "Baked goods", "determined on a case-by-case basis", ""),
        ("Treehouse Brands dba Enlightened Beverage", "Marine on St. Croix", "MN", "Frappe mix, bakery mix, coffee, and equipment", "one case 5 pouches/bags x 3 pounds", ""),
        ("Coffeewomple", "Minneapolis", "MN", "Whole bean and ground coffee", "no minimums on stock coffee options; ~16 pound minimum on custom batches", ""),
        ("European Roasterie Inc.", "Le Center", "MN", "Roasted coffee", "50 pounds per SKU", ""),
        ("Sturdiwheat Inc.", "Red Wing", "MN", "Dry mixing and packaging", "1,000 units",
         "MDA: all natural and organic certified. We do not run nuts through our system."),
        ("Particle Control Inc.", "Albertville", "MN", "Dry food ingredients", "100 pounds", ""),
        ("Crested River", "Morgan", "MN", "Gummies, chocolates, carbonated and nitrogen-dosed beverages", "", ""),
        ("NLC Beverage Company Inc.", "Rice", "MN", "Whole bean or ground coffee; ready-to-drink coffee and CBD beverage products; specialty ready-to-drink mocktails", "negotiable based on product choice", ""),
        ("Chippewa Packaging Inc.", "Saint Peter", "MN", "Snack, grains, cereal, and mixes", "to be determined", ""),
        ("Riffs Smokehouse", "Arden Hills", "MN", "BBQ and other sauces, pulled and smoked pork/chicken/beef, beef jerky, bacon jerky, and other meats", "varies by product", ""),
        ("Abdallah Candies", "Burnsville", "MN", "Candy", "varies", ""),
        ("Maud Borup", "Le Center", "MN", "Candy, snacks, dry mixes, sauces, and non-food products", "4,000 units", ""),
        ("Northwestern Foods Inc.", "Arden Hills", "MN", "Dry mixes", "2,000 pounds/item", ""),
        ("InHarvest Inc.", "Bemidji", "MN", "Grains, rice, beans, and lentils", "24 pounds stock items; 2,000 pounds custom items", ""),
        ("French Lake Butcher Shop LLC", "South Haven", "MN", "Meat and meat products", "for sausages is 20 pounds", ""),
        ("Krienke Foods International Inc.", "Mountain Lake", "MN", "Crunchy corn and legume snacks and inclusions, fried pasta snacks, trail mixes", "Negotiable", ""),
    ]
    out = []
    for name, city, st, products, moq, notes in chosen:
        rec = record(
            name=name,
            city=city,
            state_abbr=st,
            product_types=products,
            moq=moq,
            notes=notes,
            sources=[source],
        )
        out.append(rec)
    return out


def load_gap_states() -> list[dict]:
    """Companies in states that were empty or thin on a competing directory.

    Every field below was copied from the company's own public page (or is
    marked as such). Retrieved 2026-11-19.
    """
    plants = [
        {
            "name": "Griffin Food Company",
            "city": "Muskogee",
            "state_abbr": "OK",
            "address": "111 S. Cherokee",
            "zip": "74403",
            "website": "https://griffinfoods.com/private-label/",
            "phone": "",  # site said "Call us!" and listed 3579 in a truncated block; do not guess the full number
            "email": "info@griffinfoods.com",
            "product_types": "Liquid and semi-solid foods including hot sauces, mustards, imitation vanilla, corn syrup, and molasses",
            "processes": ["Private label", "Contract manufacturing", "Contract packaging", "Pump/fill for hot sauces and other liquid foods"],
            "certifications": ["SQF", "GFSI", "Kosher", "USDA Organic", "MBE"],
            "notes": "Griffin's Private Label page says it specializes in production and packaging of liquid and semi-solid foods, is GFSI certified through an annual SQF audit, packages Kosher under OU (Circle U), and has USDA Organic production certification under the Oklahoma Department of Agriculture (ODAFF). It describes itself as an experienced private label and contract manufacturer. A full phone number was not clearly captured from the page, so it is omitted here.",
            "sources": [{"name": "Griffin Foods — Private Label", "url": "https://griffinfoods.com/private-label/", "retrieved": RETRIEVED}],
        },
        {
            "name": "OWS Foods",
            "city": "Ponca City",
            "state_abbr": "OK",
            "website": "https://owsfoods.com/what-we-do/sauces-dressings-and-marinades/",
            "product_types": "BBQ sauces, marinades, and glazes; private label sauces",
            "processes": ["Sauce manufacturing", "Private label"],
            "certifications": ["GFSI"],
            "notes": "The company's sauces page describes a GFSI-certified sauce facility in Ponca City, Oklahoma, with third-party lab pathogen testing and packaging options that include pails, drums, and totes. It has a section for private-label BBQ sauces. A street address was not published in the text captured from that page.",
            "sources": [{"name": "OWS Foods — Sauces, Dressings and Marinades", "url": "https://owsfoods.com/what-we-do/sauces-dressings-and-marinades/", "retrieved": RETRIEVED}],
        },
        {
            "name": "Bakery Avenue",
            "city": "Tulsa",
            "state_abbr": "OK",
            "address": "5616 W Skelly Drive",
            "zip": "74107",
            "website": "https://www.bakeryave.com/",
            "phone": "(918) 342-5852",
            "email": "info@bakeryave.com",
            "product_types": "High volume bakery and savory products",
            "processes": ["Contract food manufacturing", "Co-packing", "Private label production"],
            "notes": "The company's website lists contract food manufacturing, co-packing, high-volume bakery and savory products, and private label production, with a Tulsa address and contact details as shown.",
            "sources": [{"name": "Bakery Avenue", "url": "https://www.bakeryave.com/", "retrieved": RETRIEVED}],
        },
        {
            "name": "Walke Brothers Meat Co.",
            "city": "Claremore",
            "state_abbr": "OK",
            "address": "9815 E 520 Road",
            "zip": "74019",
            "website": "https://walkebrothers.com/",
            "phone": "918-341-3236",
            "email": "info@walkebrothers.com",
            "product_types": "Meat, sausage, and BBQ sauce; private label and co-packing",
            "processes": ["Private labeling", "Co-packing"],
            "notes": "The company's website includes a section titled Private Label and Co-Packing Partners and says Walke Meat Company works with several companies to provide private labeling and co-packing services, including partners who ship across the country.",
            "sources": [{"name": "Walke Brothers", "url": "https://walkebrothers.com/", "retrieved": RETRIEVED}],
        },
        {
            "name": "Firefly Brew",
            "city": "Tulsa",
            "state_abbr": "OK",
            "address": "1924 E 6th St",
            "website": "https://fireflybrew.com/co-packing/",
            "phone": "(918) 886-2561",
            "product_types": "Kombucha and functional beverages; co-packing and private label",
            "processes": ["Co-packing", "Production", "Packaging", "Quality control", "Custom formulations"],
            "notes": "The company's co-packing page offers professional kombucha co-packing and private label services, mentions organic and sustainably sourced ingredients, and says services are designed to grow with a small startup or an established brand. No numeric minimum was published on that page.",
            "startup_friendly": True,
            "sources": [{"name": "Firefly Brew — Co-Packing", "url": "https://fireflybrew.com/co-packing/", "retrieved": RETRIEVED}],
        },
        {
            "name": "Focused Fluids",
            "city": "Oklahoma City",
            "state_abbr": "OK",
            "website": "https://www.focusedfluids.com/",
            "product_types": "Beverage products; formulation, development, and production",
            "processes": ["Beverage formulation", "Beverage production"],
            "moq": "Start with as little as 5,000 units",
            "notes": "The company's website says the team is centrally located in Oklahoma City and has formulated, developed, and produced beverage products. Under 'Low Minimum Orders' it states: 'Start with as little as 5,000 units. Ideal for emerging brands without high upfront…' A street address was not captured from the homepage text.",
            "startup_friendly": True,
            "sources": [{"name": "Focused Fluids", "url": "https://www.focusedfluids.com/", "retrieved": RETRIEVED}],
        },
        {
            "name": "Grand Prairie Foods",
            "city": "Sioux Falls",
            "state_abbr": "SD",
            "address": "4200 E Producer Ln",
            "zip": "57104",
            "website": "https://grandprairiefoods.com/capabilities/private-labeling/",
            "phone": "1-800-456-0532",
            "email": "info@grandprairiefoods.com",
            "product_types": "Private label and co-manufactured foods including breakfast sandwiches and other retail-ready formats",
            "processes": ["Private label", "Co-manufacturing", "In-house R&D", "Retail-ready packaging"],
            "certifications": ["SQF", "USDA inspected", "FDA registered", "Nut-free"],
            "notes": "The company's private-label page describes private label and co-manufacturing with in-house R&D, SQF Level 3 food safety, USDA inspection, FDA registration, allergen controls, and nut-free facilities. It lists product platforms such as breakfast sandwiches. Family-owned since 2003, per that page.",
            "sources": [{"name": "Grand Prairie Foods — Private Labeling", "url": "https://grandprairiefoods.com/capabilities/private-labeling/", "retrieved": RETRIEVED}],
        },
        {
            "name": "Palate Pack",
            "city": "Lincoln",
            "state_abbr": "RI",
            "website": "https://palatepack.com/",
            "product_types": "House beverages for restaurant and hospitality groups; alcoholic and non-alcoholic; canning and glass bottling",
            "processes": ["Beverage co-packing", "Canning", "Glass bottling", "Private label programs", "Ship-in repacking", "Formulation"],
            "notes": "The company's website describes beverage co-packing in Lincoln, Rhode Island, including private-label programs, canning (it mentions four can sizes from 7.…), glass bottling, alcoholic and non-alcoholic drinks, and ship-in repacking. On minimums it says production programs are built around full runs; no numeric MOQ was published in the text captured.",
            "sources": [{"name": "Palate Pack", "url": "https://palatepack.com/", "retrieved": RETRIEVED}],
        },
    ]
    out = []
    for p in plants:
        rec = record(
            name=p["name"],
            city=p["city"],
            state_abbr=p["state_abbr"],
            address=p.get("address"),
            zip=p.get("zip"),
            website=p.get("website"),
            phone=p.get("phone"),
            email=p.get("email"),
            product_types=p.get("product_types"),
            processes=p.get("processes"),
            moq=p.get("moq"),
            notes=p.get("notes"),
            startup_friendly=p.get("startup_friendly", False),
            sources=p["sources"],
        )
        if p.get("certifications"):
            rec["certifications"] = list(dict.fromkeys(p["certifications"] + rec["certifications"]))
        rec["categories"] = infer_categories(p.get("product_types") or "", " ".join(p.get("processes") or []), p.get("notes") or "")
        out.append(rec)
    return out


def dedupe(records: list[dict]) -> list[dict]:
    """Keep the first record when name+city+state collide; merge sources."""
    by_key = {}
    order = []
    for rec in records:
        key = (rec["name"].lower(), rec["city"].lower(), rec["state_abbr"])
        if key not in by_key:
            by_key[key] = rec
            order.append(key)
        else:
            existing = by_key[key]
            urls = {s["url"] for s in existing["sources"]}
            for s in rec["sources"]:
                if s["url"] not in urls:
                    existing["sources"].append(s)
    return [by_key[k] for k in order]


def main() -> None:
    records = []
    records += load_colorado()
    records += load_utah()
    records += load_minnesota()
    records += load_gap_states()
    records = dedupe(records)
    records.sort(key=lambda r: (r["state"], r["city"], r["name"]))
    # ensure unique slugs
    seen = set()
    for rec in records:
        base = rec["slug"]
        i = 2
        while rec["slug"] in seen:
            rec["slug"] = f"{base}-{i}"
            i += 1
        seen.add(rec["slug"])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated": RETRIEVED,
        "disclaimer": "Listings are compiled from public official directories and company websites. Fields that a source did not publish are left blank. Capabilities, minimums, and contacts must be reconfirmed with the plant. OpenCopack does not endorse listed companies.",
        "listings": records,
    }
    OUT.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
    print(f"Wrote {len(records)} listings to {OUT}")
    from collections import Counter
    print("by state:", dict(Counter(r["state_abbr"] for r in records)))
    print("startup_friendly:", sum(1 for r in records if r["startup_friendly"]))
    print("moq published:", sum(1 for r in records if r["moq_published"]))


if __name__ == "__main__":
    main()
