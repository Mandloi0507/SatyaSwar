"""
Stream WAV Audio Simulator.
Simulates the Flutter client streaming PCM16 chunks over WebSocket with 12-byte binary headers.
Authoritative source: Implementation.md, Section 6.2, Milestone 6 (17.2)
"""

from __future__ import annotations

import argparse
import asyncio
import json
import struct
import time
from pathlib import Path

import websockets

from satyaswar_ml.audio.io import float32_to_pcm16le, load_audio


async def stream_audio_file(
    wav_path: str | Path,
    server_ws_url: str = "ws://127.0.0.1:8100/ml/ws/sim_call_01",
    telephony_profile: str = "none",
    fast: bool = False,
    contacts_file: str | None = None,
) -> None:
    print(f"Loading {wav_path}...")
    audio, sr = load_audio(wav_path)
    print(f"Loaded {len(audio)} samples at {sr} Hz ({len(audio)/sr:.2f} seconds)")

    contacts = []
    if contacts_file and Path(contacts_file).is_file():
        with open(contacts_file, "r", encoding="utf-8") as f:
            contacts = json.load(f)

    # 1.75s chunk = 28,000 samples
    chunk_samples = 28000
    chunk_duration_s = chunk_samples / sr

    print(f"Connecting to {server_ws_url}...")
    async with websockets.connect(server_ws_url) as ws:
        print("Connected!")

        # 1. Send session_start JSON message
        start_msg = {
            "schema_version": "1.0",
            "type": "session_start",
            "call_id": "sim_call_01",
            "mode": "chunks",
            "telephony_profile": telephony_profile,
            "contacts": contacts,
            "resume": False,
        }
        await ws.send(json.dumps(start_msg))

        # Start listener task for incoming downstream events
        events_received = []

        async def listener():
            try:
                async for msg in ws:
                    event = json.loads(msg)
                    events_received.append(event)
                    ev_type = event.get("type")
                    if ev_type == "score":
                        idx = event.get("window_index")
                        band = event.get("band")
                        score = event.get("spoof_score")
                        lat = event.get("latency_ms", {}).get("total")
                        print(f"  [SCORE] Win {idx}: Band={band}, Spoof={score}, Latency={lat}ms")
                    elif ev_type == "alert":
                        lvl = event.get("level")
                        txt = event.get("text", {}).get("en")
                        print(f"  *** [ALERT {lvl.upper()}] {txt} ***")
                    elif ev_type == "session_ready":
                        dev = event.get("device")
                        print(f"  [READY] Engine initialized on device={dev}")
                    elif ev_type == "call_summary":
                        print("  [SUMMARY] Call ended. Summary received.")
                    else:
                        print(f"  [{ev_type.upper()}] {event}")
            except websockets.ConnectionClosed:
                pass

        listen_task = asyncio.create_task(listener())

        # 2. Stream binary frames: 12-byte header + PCM16 chunk
        n_chunks = int(np.ceil(len(audio) / chunk_samples))
        t_stream_start = time.time()

        for seq in range(n_chunks):
            start_idx = seq * chunk_samples
            end_idx = min(len(audio), (seq + 1) * chunk_samples)
            chunk_audio = audio[start_idx:end_idx]

            # Convert to PCM16
            pcm_payload = float32_to_pcm16le(chunk_audio)
            client_ts_ms = int(time.time() * 1000)

            # Build 12-byte header: uint32 seq | uint64 client_ts_ms (little-endian)
            header = struct.pack("<IQ", seq, client_ts_ms)
            frame_bytes = header + pcm_payload

            await ws.send(frame_bytes)

            if not fast:
                await asyncio.sleep(chunk_duration_s)

        # 3. Send session_end message
        await asyncio.sleep(1.0)
        await ws.send(json.dumps({"schema_version": "1.0", "type": "session_end"}))
        await asyncio.sleep(1.0)

        listen_task.cancel()
        print("\n=== Stream Session Summary ===")
        print(f"Total events received: {len(events_received)}")
        scores = [e for e in events_received if e.get("type") == "score"]
        if scores:
            latencies = [e.get("latency_ms", {}).get("total", 0.0) for e in scores]
            print(f"Scored windows: {len(scores)}")
            print(f"Mean window latency: {np.mean(latencies):.1f} ms")


if __name__ == "__main__":
    import numpy as np

    parser = argparse.ArgumentParser(description="SatyaSwar Audio Stream Simulator")
    parser.add_argument("wav", nargs="?", default="vad_test.wav", help="Path to audio WAV file")
    parser.add_argument("--url", default="ws://127.0.0.1:8100/ml/ws/sim_call_01", help="WebSocket URL")
    parser.add_argument("--telephony", default="none", help="Telephony profile (none, g711_ulaw, etc.)")
    parser.add_argument("--fast", action="store_true", help="Send chunks as fast as possible")
    parser.add_argument("--contacts", default=None, help="JSON file with contacts")
    args = parser.parse_args()

    asyncio.run(
        stream_audio_file(
            wav_path=args.wav,
            server_ws_url=args.url,
            telephony_profile=args.telephony,
            fast=args.fast,
            contacts_file=args.contacts,
        )
    )
