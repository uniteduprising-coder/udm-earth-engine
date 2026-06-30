#!/usr/bin/env python3
"""Execute UDM Master Encyclopedia ingestion pipeline."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth.cosmology.encyclopedia import ingest_encyclopedia


def main() -> None:
    result = ingest_encyclopedia()
    print(json.dumps(result, indent=2))
    if not result.get("ok"):
        sys.exit(1)


if __name__ == "__main__":
    main()