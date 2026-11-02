"""Check real portfolio quotes against Yahoo Finance."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.main import get_realtime_portfolio  # noqa: E402


def main() -> int:
    data = get_realtime_portfolio()
    if not data:
        raise RuntimeError("The market API returned no positions")

    print(f"ITEMS={len(data)}")
    for position in data:
        print(
            f"{position['marketSymbol']} | {position['marketPrice']} "
            f"{position['marketCurrency']} -> {position['price']} EUR | "
            f"change {position['changePercent']}% | {position['dataSource']}"
        )
    print(f"TOTAL_EUR={round(sum(position['value'] for position in data), 2)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())