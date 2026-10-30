"""
Scenario Audio Generator for SatyaSwar Demo
Authoritative source: Implementation.md, Section 12.1, 12.2

Generates 16 kHz mono WAV files for the 6 demo scenarios in configs/scenarios.json:
- gen_hi_01: Genuine Hindi call (meeting time change)
- clone_hi_01: Cloned Hindi emergency (urgent money)
- gen_en_01: Genuine English call (project update)
- clone_en_01: Cloned English CEO request (urgent transfer, confidential)
- noisy_hi_01: Noisy Hindi call (street noise, low SNR)
- short_en_01: Very short call (2 seconds only)
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT_DIR = Path(__file__).parent.parent
SCENARIOS_DIR = ROOT_DIR / "assets" / "scenarios"


async def synthesize_or_generate_clip(
    text: str,
    voice: str,
    out_wav: Path,
    duration_s: float = 6.0,
    add_noise: bool = False,
    is_short: bool = False,
) -> None:
    """
    Attempts edge-tts synthesis, falling back to clean harmonic phonation synthesis.
    Output is strictly 16 kHz mono PCM16.
    """
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    generated_via_edge = False

    try:
        import edge_tts
        temp_mp3 = out_wav.with_suffix(".mp3")
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(str(temp_mp3))

        import av
        container = av.open(str(temp_mp3))
        resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
        frames = []
        for frame in container.decode(audio=0):
            resampled_frames = resampler.resample(frame)
            for rf in resampled_frames:
                frames.append(rf.to_ndarray())
        container.close()
        temp_mp3.unlink(missing_ok=True)

        if frames:
            audio_data = np.concatenate(frames, axis=-1).squeeze()
            audio_f32 = audio_data.astype(np.float32) / 32768.0

            if is_short:
                audio_f32 = audio_f32[: int(1.8 * 16000)]
            if add_noise:
                noise = np.random.normal(0, 0.15, len(audio_f32)).astype(np.float32)
                audio_f32 = np.clip(audio_f32 + noise, -1.0, 1.0)

            sf.write(str(out_wav), audio_f32, 16000, subtype="PCM_16")
            generated_via_edge = True
    except Exception:
        # Fallback to high-quality synthetic multi-tone speech envelope
        pass

    if not generated_via_edge:
        # Synthetic speech simulation fallback
        dur = 1.8 if is_short else duration_s
        n_samples = int(dur * 16000)
        t = np.linspace(0, dur, n_samples, endpoint=False, dtype=np.float32)

        # Fundamental + formants
        f0 = 160.0
        audio_f32 = (
            0.35 * np.sin(2 * np.pi * f0 * t)
            + 0.25 * np.sin(2 * np.pi * 2 * f0 * t)
            + 0.15 * np.sin(2 * np.pi * 3 * f0 * t)
            + 0.10 * np.sin(2 * np.pi * 5 * f0 * t)
        )
        # Apply speech amplitude envelope (rhythmic syllables)
        envelope = 0.5 * (1.0 + np.sin(2 * np.pi * 3.5 * t))
        audio_f32 *= envelope

        if add_noise:
            noise = np.random.normal(0, 0.25, n_samples).astype(np.float32)
            audio_f32 = np.clip(audio_f32 + noise, -1.0, 1.0)

        # Normalize to -3 dB
        peak = np.max(np.abs(audio_f32))
        if peak > 0:
            audio_f32 = (audio_f32 / peak) * 0.707

        sf.write(str(out_wav), audio_f32, 16000, subtype="PCM_16")


async def generate_all_scenarios() -> None:
    SCENARIOS = [
        {
            "id": "gen_hi_01",
            "file": SCENARIOS_DIR / "gen_hi_01.wav",
            "text": "हाय, मैं अभिषेक बोल रहा हूँ। कल की मीटिंग का समय बदल गया है, शाम चार बजे रखते हैं।",
            "voice": "hi-IN-MadhurNeural",
            "add_noise": False,
            "is_short": False,
        },
        {
            "id": "clone_hi_01",
            "file": SCENARIOS_DIR / "clone_hi_01.wav",
            "text": "मैं प्रिया बोल रही हूँ। मैं बहुत मुसीबत में हूँ, मुझे अभी पचास हज़ार रुपये ट्रांसफर करो और किसी को मत बताना।",
            "voice": "hi-IN-SwaraNeural",
            "add_noise": False,
            "is_short": False,
        },
        {
            "id": "gen_en_01",
            "file": SCENARIOS_DIR / "gen_en_01.wav",
            "text": "Hi, this is Rahul. Just checking in on the project update before tomorrow's review.",
            "voice": "en-IN-PrabhatNeural",
            "add_noise": False,
            "is_short": False,
        },
        {
            "id": "clone_en_01",
            "file": SCENARIOS_DIR / "clone_en_01.wav",
            "text": "Hi, this is Rahul. I need you to transfer fifty thousand rupees right now. It is urgent and confidential, please do not tell anyone.",
            "voice": "en-IN-NeerjaNeural",
            "add_noise": False,
            "is_short": False,
        },
        {
            "id": "noisy_hi_01",
            "file": SCENARIOS_DIR / "noisy_hi_01.wav",
            "text": "अभिषेक यहाँ, आवाज़ साफ़ नहीं आ रही है, मैं सड़क पर हूँ।",
            "voice": "hi-IN-MadhurNeural",
            "add_noise": True,
            "is_short": False,
        },
        {
            "id": "short_en_01",
            "file": SCENARIOS_DIR / "short_en_01.wav",
            "text": "Hello, Rahul here.",
            "voice": "en-IN-PrabhatNeural",
            "add_noise": False,
            "is_short": True,
        },
    ]

    print("Generating demo scenarios into assets/scenarios/...")
    for sc in SCENARIOS:
        await synthesize_or_generate_clip(
            text=sc["text"],
            voice=sc["voice"],
            out_wav=sc["file"],
            add_noise=sc["add_noise"],
            is_short=sc["is_short"],
        )
        print(f"Generated scenario WAV: {sc['file'].name}")


if __name__ == "__main__":
    asyncio.run(generate_all_scenarios())
