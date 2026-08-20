"""Quick WS watcher against the live uvicorn server (background task) to
prove the production path (not TestClient) emits the same envelopes."""
import asyncio
import json
import sys

import websockets

URI = sys.argv[1] if len(sys.argv) > 1 else "ws://127.0.0.1:8765/ws/feed"
MAX_MSGS = int(sys.argv[2]) if len(sys.argv) > 2 else 12


async def watch():
    print(f"Connected to {URI}")
    async with websockets.connect(URI) as ws:
        for i in range(MAX_MSGS):
            raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            msg = json.loads(raw)
            t = msg.get("type")
            if t == "telemetry_update":
                rp = msg["risk_prediction"]
                zid = rp["zone_id"]
                rl = rp["risk_level"]
                sc = rp["risk_score"]
                print(f"  [msg {i:2d}] telemetry zone={zid:8s} risk={rl} score={sc:.3f}")
            elif t == "alert_event":
                a = msg["alert"]
                zid = a["zone_id"]
                sev = a["severity"]
                aid = a["alert_id"]
                print(f"  [msg {i:2d}] ALERT    zone={zid:8s} severity={sev:12s} id={aid}")
                print(f"           message: {a['message']}")
            else:
                print(f"  [msg {i:2d}] unknown type: {t}")


if __name__ == "__main__":
    asyncio.run(watch())
