#!/usr/bin/env python3
"""Launch UDM Real-Time Earth Model pipeline (plate-locked overlay integration)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from earth.realtime.pipeline import run_realtime_pipeline_sync


def main() -> int:
    report = run_realtime_pipeline_sync()
    print(json.dumps({
        "ok": report["ok"],
        "plate_lock_preserved": report["plate_lock_preserved"],
        "plates_present": report["plates_present"],
        "control_grade": report["derived"]["control_grade"],
        "validation": f"{report['validation']['passed']}/{report['validation']['total']}",
        "needs_manual_review": report["needs_manual_review"],
        "failed_pulls": report["failed"],
        "stale_sources": report["stale"],
    }, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())