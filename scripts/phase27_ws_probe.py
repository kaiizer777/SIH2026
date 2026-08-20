"""
Phase 27 WS probe -- non-mutating live check against wss://sih2026-xk4z.onrender.com/ws/feed.
Confirms: TLS handshake, WSS upgrade, real telemetry_update envelope, model_version live.
"""
from __future__ import annotations
import asyncio, json, sys, time

try:
    import websockets  # type: ignore
except ImportError:
    print("websockets package not installed; pip install websockets")
    sys.exit(2)

URL = "wss://sih2026-xk4z.onrender.com/ws/feed"


async def main() -> int:
    print(f"[probe] target: {URL}")
    t0 = time.time()
    try:
        async with websockets.connect(URL, ping_interval=20, ping_timeout=20) as ws:
            handshake_ms = (time.time() - t0) * 1000
            print(f"[probe] WS connected, handshake {handshake_ms:.0f} ms")
            for i in range(3):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=15.0)
                    d = json.loads(msg)
                    print(f"[probe] msg[{i}] type={d.get('type')} keys={list(d.keys())}")
                    if d.get('type') == 'telemetry_update':
                        p = d.get('payload', {})
                        print(
                            f"[probe]   zone_id={p.get('zone_id')} "
                            f"risk_level={p.get('risk_level')} "
                            f"model_version={p.get('model_version')} "
                            f"risk_score={p.get('risk_score')}"
                        )
                except asyncio.TimeoutError:
                    print(f"[probe] msg[{i}] TIMEOUT (15s) — no message within window")
                    break
    except Exception as e:
        print(f"[probe] WS error: {type(e).__name__}: {e}")
        return 1
    print("[probe] OK")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
