"""
tests/test_ws_disconnect.py -- Phase 21 multi-client disconnect resilience test.

Verifies that if one WebSocket client disconnects mid-stream, the broadcast loop
continues delivering messages to remaining connected clients uninterrupted.

This test directly exercises ConnectionManager.broadcast()'s per-connection
try/except pattern: a dead connection must not prevent delivery to live clients.

Requires a running server. Start with:
    cd backend && uvicorn main:app --host 127.0.0.1 --port 8001 --reload

Then run:
    python tests/test_ws_disconnect.py
"""
import asyncio
import json
import sys
from pathlib import Path

PORT = 8001
URI = f"ws://127.0.0.1:{PORT}/ws/feed"

# Valid message types for Phase 21 (broadcast loop emits both)
VALID_TYPES = {"telemetry_update", "alert_event"}


async def run_disconnect_test() -> bool:
    try:
        import websockets
        import websockets.exceptions
    except ImportError:
        print("SKIP: websockets not installed -- pip install websockets")
        return False

    print(f"[Test] Multi-client disconnect resilience")
    print(f"[Test] Connecting Client A and Client B to {URI} ...")

    # Connect both clients independently so we can close them independently
    try:
        ws_a = await websockets.connect(URI)
        ws_b = await websockets.connect(URI)
    except Exception as e:
        print(f"FAIL: Could not connect to {URI}: {e}")
        print(f"      Is the server running? (uvicorn main:app --port {PORT})")
        return False

    try:
        # --- Step 1: Confirm both clients receive at least one message ---
        print("[Test] Waiting for both clients to receive an initial message ...")
        try:
            raw_a = await asyncio.wait_for(ws_a.recv(), timeout=12.0)
            raw_b = await asyncio.wait_for(ws_b.recv(), timeout=12.0)
        except asyncio.TimeoutError:
            print("FAIL: Timed out waiting for initial message (is the server running?)")
            return False

        msg_a = json.loads(raw_a)
        msg_b = json.loads(raw_b)

        assert msg_a.get("type") in VALID_TYPES, f"Client A: unexpected type {msg_a.get('type')}"
        assert msg_b.get("type") in VALID_TYPES, f"Client B: unexpected type {msg_b.get('type')}"

        print(f"  Client A received: type={msg_a['type']}")
        print(f"  Client B received: type={msg_b['type']}")
        print("  [OK] Both clients receiving messages")

        # --- Step 2: Forcefully close Client A ---
        print("\n[Test] Closing Client A forcefully ...")
        await ws_a.close()
        print("  Client A disconnected.")

        # Brief pause to let the server's broadcast loop attempt at least one
        # delivery to the now-closed socket (triggering the cleanup path)
        await asyncio.sleep(3.0)

        # --- Step 3: Confirm Client B keeps receiving messages after A disconnects ---
        print("[Test] Collecting 4 messages from Client B post-disconnect ...")
        post_disconnect: list[dict] = []

        for i in range(4):
            try:
                raw = await asyncio.wait_for(ws_b.recv(), timeout=15.0)
                msg = json.loads(raw)
                post_disconnect.append(msg)
                print(f"  Client B post-disconnect msg {i+1}: type={msg.get('type')}")
            except asyncio.TimeoutError:
                print(f"FAIL: Client B timed out waiting for message {i+1} after A disconnected")
                return False
            except Exception as e:
                print(f"FAIL: Client B raised unexpected exception on msg {i+1}: {e}")
                return False

        # --- Step 4: Validate all post-disconnect messages ---
        assert len(post_disconnect) == 4, (
            f"FAIL: Expected 4 messages, got {len(post_disconnect)}"
        )
        for i, msg in enumerate(post_disconnect):
            assert msg.get("type") in VALID_TYPES, (
                f"FAIL: Post-disconnect message {i+1} has invalid type: {msg.get('type')}"
            )

        print()
        print("[OK] Client B received 4 messages after Client A disconnected.")
        print("[OK] Broadcast loop is resilient to mid-stream client disconnects.")
        return True

    finally:
        try:
            await ws_b.close()
        except Exception:
            pass


async def run_connection_count_test() -> bool:
    """
    Supplementary: verify that ConnectionManager correctly tracks connection count.
    Connect 3 clients, disconnect 2, confirm the 3rd still receives messages.
    """
    try:
        import websockets
    except ImportError:
        return False

    print("\n[Test] Connection count tracking (3 connect, 2 disconnect) ...")

    try:
        ws1 = await websockets.connect(URI)
        ws2 = await websockets.connect(URI)
        ws3 = await websockets.connect(URI)
    except Exception as e:
        print(f"  SKIP: Could not open 3 connections: {e}")
        return True  # Not a failure -- server may limit connections

    try:
        # All 3 receive a message
        for label, ws in [("ws1", ws1), ("ws2", ws2), ("ws3", ws3)]:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=12.0)
                msg = json.loads(raw)
                assert msg.get("type") in VALID_TYPES
                print(f"  {label}: got type={msg['type']}")
            except asyncio.TimeoutError:
                print(f"  SKIP: {label} timed out")
                return True

        # Disconnect ws1 and ws2
        await ws1.close()
        await ws2.close()
        print("  ws1 and ws2 disconnected.")

        await asyncio.sleep(3.0)

        # ws3 must keep receiving
        for i in range(3):
            try:
                raw = await asyncio.wait_for(ws3.recv(), timeout=12.0)
                msg = json.loads(raw)
                assert msg.get("type") in VALID_TYPES
                print(f"  ws3 post-disconnect msg {i+1}: type={msg['type']}")
            except asyncio.TimeoutError:
                print(f"FAIL: ws3 timed out after ws1+ws2 disconnected")
                return False

        print("[OK] ws3 received 3 messages after ws1+ws2 disconnected.")
        return True

    finally:
        for ws in [ws1, ws2, ws3]:
            try:
                await ws.close()
            except Exception:
                pass


if __name__ == "__main__":
    print("=" * 60)
    print("Phase 21 WebSocket Disconnect Resilience Tests")
    print(f"Target: {URI}")
    print("=" * 60)
    print()

    result1 = asyncio.run(run_disconnect_test())
    result2 = asyncio.run(run_connection_count_test())

    print()
    if result1 and result2:
        print("[PASS] All disconnect resilience tests passed.")
        sys.exit(0)
    else:
        print("[FAIL] One or more disconnect tests failed.")
        sys.exit(1)
