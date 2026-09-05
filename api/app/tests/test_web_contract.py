import json
import subprocess
from pathlib import Path


def test_real_api_payloads_satisfy_website_contract(client, staff, demo_cases, tmp_path):
    root = Path(__file__).resolve().parents[3]
    payloads = {
        "caseSchema": client.get("/api/v1/disputes/CB-DEMO-01", headers=staff["viewer"][1]).json(),
        "disputeListSchema": client.get("/api/v1/disputes", headers=staff["viewer"][1]).json(),
        "overviewSchema": client.get("/api/v1/overview", headers=staff["viewer"][1]).json(),
        "policiesSchema": client.get("/api/v1/policies", headers=staff["viewer"][1]).json(),
    }
    payload_path = tmp_path / "contract.json"
    payload_path.write_text(json.dumps(payloads), encoding="utf-8")
    script = tmp_path / "check.mjs"
    script.write_text(
        f'import * as schemas from "{(root / "src/lib/ops-schemas.ts").as_uri()}";\n'
        'import fs from "node:fs";\n'
        f'const payloads = JSON.parse(fs.readFileSync({json.dumps(str(payload_path))}, "utf8"));\n'
        'for (const [name, payload] of Object.entries(payloads)) schemas[name].parse(payload);\n', encoding="utf-8")
    result = subprocess.run(["node", "--experimental-strip-types", str(script)], capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
