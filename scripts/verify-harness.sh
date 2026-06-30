#!/usr/bin/env bash
set -euo pipefail
export PYTHONPATH=src
python -m pytest tests/ -q
echo "udm-earth-engine harness OK"