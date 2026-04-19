from __future__ import annotations

import urllib.parse
import urllib.request

URL = "http://localhost:8000/search"


def main() -> int:
    query = urllib.parse.urlencode(
        {
            "q": "札幌",
            "layout": "2LDK",
            "price_lte": "90000",
            "pet": "true",
        }
    )
    with urllib.request.urlopen(f"{URL}?{query}", timeout=10) as resp:
        print(resp.read().decode("utf-8", errors="replace"), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
