#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
code = (ROOT / "worker/dist/standalone.mjs").read_text(encoding="utf-8")
js = (
    "async () => {\n"
    f"  const code = {json.dumps(code)};\n"
    "  const metadata = { main_module: 'standalone.mjs', compatibility_date: '2024-11-01' };\n"
    "  const b = 'FormBoundary' + Date.now();\n"
    "  const body = [\n"
    "    '--' + b,\n"
    '    \'Content-Disposition: form-data; name="metadata"\',\n'
    "    'Content-Type: application/json',\n"
    "    '',\n"
    "    JSON.stringify(metadata),\n"
    "    '--' + b,\n"
    '    \'Content-Disposition: form-data; name="standalone.mjs"; filename="standalone.mjs"\',\n'
    "    'Content-Type: application/javascript+module',\n"
    "    '',\n"
    "    code,\n"
    "    '--' + b + '--'\n"
    "  ].join('\\r\\n');\n"
    "  const upload = await cloudflare.request({\n"
    "    method: 'PUT',\n"
    "    path: `/accounts/${accountId}/workers/scripts/udm-earth-engine`,\n"
    "    body,\n"
    "    contentType: 'multipart/form-data; boundary=' + b,\n"
    "    rawBody: true\n"
    "  });\n"
    "  return { upload, scriptBytes: code.length };\n"
    "}"
)
out = ROOT / "worker/dist/deploy_mcp.json"
out.write_text(json.dumps({"code": js}), encoding="utf-8")
print(f"Wrote {out} ({len(js)} chars)")