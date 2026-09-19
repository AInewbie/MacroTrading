"""Bounded public-source acquisition. Retrieved headlines remain unaccepted candidates."""

from __future__ import annotations
import csv
import hashlib
import io
import ipaddress
import socket
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from urllib.parse import urlsplit, urljoin
from urllib.request import Request, build_opener, HTTPRedirectHandler
from .validation import (
    digest,
    instant,
    stamp,
    text,
    identifier,
    boolean,
    number,
    url,
)
from .models import MarketClose

MAX_BYTES = 2_000_000


class PlainText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, value):
        self.parts.append(value)


def plain(value):
    p = PlainText()
    p.feed(value or "")
    return " ".join(" ".join(p.parts).split())


def validate_sources(sources):
    if not isinstance(sources, list) or len(sources) > 50:
        raise ValueError("sources must contain at most 50 entries")
    ids = set()
    for s in sources:
        identifier(s.get("id"))
        text(s.get("name"), "source name", 200)
        boolean(s.get("enabled"), "source enabled")
        if s["id"] in ids:
            raise ValueError("duplicate source id")
        ids.add(s["id"])
        if s.get("kind") not in ("rss", "ecb_fx", "market_csv"):
            raise ValueError("source kind must be rss, ecb_fx or market_csv")
        u = urlsplit(url(s["url"]))
        if u.scheme != "https" or u.port not in (None, 443):
            raise ValueError("acquisition requires HTTPS on port 443")
        if (
            not isinstance(s.get("allowed_hosts"), list)
            or not s["allowed_hosts"]
            or u.hostname not in s["allowed_hosts"]
        ):
            raise ValueError("source host must be explicitly allowed")
        for h in s["allowed_hosts"]:
            if not isinstance(h, str) or "/" in h or ":" in h or "*" in h:
                raise ValueError("allowed_hosts requires exact DNS names")
        if s.get("theme_ids") and (
            not isinstance(s["theme_ids"], list)
            or any(not isinstance(t, str) for t in s["theme_ids"])
        ):
            raise ValueError("theme_ids must be an array")
    return sources


def validate_public_url(value, hosts):
    u = urlsplit(value)
    if (
        u.scheme != "https"
        or u.hostname not in hosts
        or u.username
        or u.password
        or u.port not in (None, 443)
    ):
        raise ValueError("destination is outside the approved HTTPS source")
    addresses = socket.getaddrinfo(u.hostname, 443, type=socket.SOCK_STREAM)
    if not addresses or any(
        not ipaddress.ip_address(a[4][0]).is_global for a in addresses
    ):
        raise ValueError("source must resolve only to public addresses")


class Redirects(HTTPRedirectHandler):
    def __init__(self, hosts):
        self.hosts = hosts

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_public_url(newurl, self.hosts)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def fetch_bytes(source):
    validate_sources([source])
    validate_public_url(source["url"], source["allowed_hosts"])
    req = Request(
        source["url"],
        headers={
            "User-Agent": "MacroTrading/0.5 (personal research reader)",
            "Accept": "application/xml,application/rss+xml,text/csv,*/*;q=0.1",
        },
    )
    with build_opener(Redirects(source["allowed_hosts"])).open(
        req, timeout=10
    ) as response:
        data = response.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise ValueError("source exceeds 2 MB limit")
        return data


def xml_root(raw):
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("XML declarations with entities are not accepted")
    return ET.fromstring(raw)


def parse_feed(raw, source, retrieved_at):
    root = xml_root(raw)
    items = []
    warnings = []
    h = hashlib.sha256(raw).hexdigest()
    atom = "{http://www.w3.org/2005/Atom}"
    entries = root.findall(".//item") or root.findall(".//" + atom + "entry")
    for entry in entries[:100]:

        def value(name):
            return entry.findtext(name) or entry.findtext(atom + name)

        title = plain(value("title"))
        summary = plain(
            value("description") or value("summary") or value("content") or title
        )
        link = value("link")
        if not link:
            node = entry.find(atom + "link")
            link = node.get("href") if node is not None else None
        pub = (
            value("pubDate")
            or value("published")
            or value("updated")
            or entry.findtext("{http://purl.org/dc/elements/1.1/}date")
        )
        if not title or not link or not pub:
            warnings.append("Skipped entry without title, URL or publication date")
            continue
        try:
            try:
                published = stamp(instant(pub))
            except ValueError:
                dt = parsedate_to_datetime(pub)
                if dt.tzinfo is None:
                    raise ValueError("feed date needs timezone")
                published = stamp(dt)
            if instant(published) > instant(retrieved_at):
                raise ValueError("future publication")
            link = url(urljoin(source["url"], link))
        except (ValueError, TypeError):
            warnings.append("Skipped malformed or future-dated entry")
            continue
        candidate = {
            "title": title[:500],
            "summary": summary[:6000],
            "url": link,
            "published_at": published,
            "retrieved_at": retrieved_at,
            "content_hash": h,
            "source_group": source.get("source_group", source["id"]),
            "suggested_themes": source.get("theme_ids", []),
            "kind": "unclassified",
            "review_required": True,
        }
        candidate["id"] = (
            "feed-"
            + digest(
                {
                    k: candidate[k]
                    for k in ("title", "summary", "url", "published_at", "source_group")
                }
            )[:32]
        )
        items.append(candidate)
    return {"candidates": items, "warnings": warnings, "content_hash": h}


def parse_fx(raw, retrieved_at):
    root = xml_root(raw)
    rates = []
    for day in root.iter():
        if "time" not in day.attrib:
            continue
        at = day.attrib["time"] + "T00:00:00Z"
        if instant(at) > instant(retrieved_at):
            raise ValueError("future reference FX date")
        for cube in day:
            if "currency" in cube.attrib and "rate" in cube.attrib:
                rates.append(
                    {
                        "from": "EUR",
                        "to": cube.attrib["currency"],
                        "rate": number(float(cube.attrib["rate"]), "FX rate", 1e-12),
                        "as_of": at,
                        "source": "ECB daily reference (date precision)",
                    }
                )
    if not rates:
        raise ValueError("no ECB reference rates found")
    return {
        "fx_rates": rates,
        "warnings": [],
        "content_hash": hashlib.sha256(raw).hexdigest(),
    }


def parse_market_csv(raw):
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8-sig")
    rows = []
    for r in csv.DictReader(io.StringIO(raw)):
        if len(rows) >= 5000:
            raise ValueError("market CSV exceeds 5000 rows")
        r = {k: v for k, v in r.items() if v != ""}
        for k in (
            "proxy_close",
            "benchmark_close",
            "proxy_return_pct",
            "benchmark_return_pct",
        ):
            if k in r:
                r[k] = float(r[k])
        if r.get("completed") not in ("true", "false"):
            raise ValueError("CSV completed must be true or false")
        r["completed"] = r["completed"] == "true"
        rows.append(MarketClose.from_dict(r).to_dict())
    if not rows:
        raise ValueError("market CSV is empty")
    return {"market_closes": rows, "warnings": []}


def acquire(source, now=None, fetcher=fetch_bytes):
    now = now or stamp()
    raw = fetcher(source)
    parsed = (
        parse_feed(raw, source, now)
        if source["kind"] == "rss"
        else parse_fx(raw, now)
        if source["kind"] == "ecb_fx"
        else parse_market_csv(raw)
    )
    parsed["content_hash"] = hashlib.sha256(raw).hexdigest()
    return raw, parsed
