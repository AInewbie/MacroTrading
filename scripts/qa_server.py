"""Isolated synthetic browser test server. Never operates on user state."""

import argparse
from datetime import date, timedelta
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from macrotrading.service import Service
from macrotrading.server import AppServer
from macrotrading.validation import canonical, stamp, instant
from macrotrading.calendars import is_session


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    args = parser.parse_args()
    calendars = json.loads((ROOT / "config/calendars.json").read_text())
    days = []
    day = date.today() - timedelta(days=1)
    while len(days) < 5:
        if is_session(day, calendars["ECB_REFERENCE_2026_2028"]):
            days.append(day)
        day -= timedelta(days=1)
        if (date.today() - day).days > 15:
            raise ValueError("QA date outside configured calendars")
    days.sort()
    xml = (
        "<Envelope><Cube>"
        + "".join(
            f'<Cube time="{d}"><Cube currency="USD" rate="{1.1 + n * 0.001}"/></Cube>'
            for n, d in enumerate(days)
        )
        + "</Cube></Envelope>"
    ).encode()

    class FixtureService(Service):
        def market_refresh(self, body):
            return super().market_refresh(body, fetcher=lambda source: xml)

    with TemporaryDirectory(prefix="macrotrading-browser-") as directory:
        service = FixtureService(ROOT, directory)
        at = stamp()
        published = stamp(instant(at) - timedelta(minutes=2))
        with service.store.transaction() as db:
            for n in range(2):
                c = {
                    "id": f"browser-{n}",
                    "title": f"Inflation outlook {n}",
                    "summary": "Synthetic browser test evidence about inflation.",
                    "url": f"https://example.com/browser-{n}",
                    "published_at": published,
                    "retrieved_at": at,
                    "content_hash": "b" * 64,
                    "source_group": f"fixture-{n}",
                }
                db.execute(
                    "INSERT INTO inbox(id,source_id,first_known_at,payload) VALUES(?,?,?,?)",
                    (c["id"], "browser-fixture", at, canonical(c)),
                )
        server = AppServer(("127.0.0.1", args.port), service)
        try:
            server.serve_forever()
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
