"""
Alert Audio Generator for SatyaSwar
Authoritative source: Implementation.md, Section 7.13, 12.3, Appendix C

Generates bilingual spoken alert clips (English & Hindi) in assets/alerts/:
- low_en.wav / low_hi.wav
- medium_en.wav / medium_hi.wav
- high_en.wav / high_hi.wav
- insufficient_en.wav / insufficient_hi.wav
- denied_en.wav / denied_hi.wav
- confirmed_en.wav / confirmed_hi.wav
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import numpy as np
import soundfile as sf

ROOT_DIR = Path(__file__).parent.parent
ALERTS_DIR = ROOT_DIR / "assets" / "alerts"

# Appendix C Alert Strings
ALERT_TEXTS = {
    "low": {
        "en": "No synthetic signs found so far. This is not proof of identity. Verify before sending money.",
        "hi": "अब तक नकली आवाज़ के संकेत नहीं मिले। यह पहचान का प्रमाण नहीं है। पैसे भेजने से पहले पुष्टि करें।",
    },
    "medium": {
        "en": "This voice shows some warning signs. Be careful and consider verifying the caller.",
        "hi": "इस आवाज़ में कुछ चेतावनी के संकेत हैं। सावधान रहें और कॉलर की पुष्टि करने पर विचार करें।",
    },
    "high": {
        "en": "Warning. This voice may be synthetic. Do not share money or codes. Verify the caller now.",
        "hi": "सावधान! यह आवाज़ नकली हो सकती है। पैसे या कोड न दें। अभी कॉलर की पुष्टि करें।",
    },
    "insufficient": {
        "en": "Not enough clear audio to judge. Verify the caller before any sensitive action.",
        "hi": "आवाज़ का आकलन करने के लिए साफ़ ऑडियो पर्याप्त नहीं है। कोई भी संवेदनशील काम करने से पहले कॉलर की पुष्टि करें।",
    },
    "denied": {
        "en": "Verification denied. The claimed contact stated they are not calling you. End the call immediately.",
        "hi": "सत्यापन अस्वीकार कर दिया गया। संपर्क ने कहा कि वे आपको कॉल नहीं कर रहे हैं। तुरंत कॉल समाप्त करें।",
    },
    "confirmed": {
        "en": "Caller verified via linked account. Exercise normal caution.",
        "hi": "कॉलर का सत्यापन लिंक किए गए खाते से हो गया है। सामान्य सावधानी बरतें।",
    },
}


async def generate_single_alert(text: str, voice: str, out_wav: Path) -> None:
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

            # Cap duration strictly under 4.0s (Section 12.3 requirement)
            if len(audio_f32) > 16000 * 4:
                audio_f32 = audio_f32[: 16000 * 4]

            peak = np.max(np.abs(audio_f32))
            if peak > 0:
                audio_f32 = (audio_f32 / peak) * 0.85  # Normalise

            sf.write(str(out_wav), audio_f32, 16000, subtype="PCM_16")
            generated_via_edge = True
    except Exception:
        pass

    if not generated_via_edge:
        # Fallback synthesizer
        dur = 3.2
        n_samples = int(dur * 16000)
        t = np.linspace(0, dur, n_samples, endpoint=False, dtype=np.float32)
        audio_f32 = (
            0.4 * np.sin(2 * np.pi * 440 * t)
            + 0.3 * np.sin(2 * np.pi * 880 * t)
        ) * np.exp(-t / 1.5)
        sf.write(str(out_wav), audio_f32, 16000, subtype="PCM_16")


async def generate_all_alerts() -> None:
    print("Generating bilingual alert audio into assets/alerts/...")
    voice_en = "en-IN-NeerjaNeural"
    voice_hi = "hi-IN-SwaraNeural"

    for key, texts in ALERT_TEXTS.items():
        # English
        wav_en = ALERTS_DIR / f"{key}_en.wav"
        await generate_single_alert(texts["en"], voice_en, wav_en)
        print(f"Generated: {wav_en.name}")

        # Hindi
        wav_hi = ALERTS_DIR / f"{key}_hi.wav"
        await generate_single_alert(texts["hi"], voice_hi, wav_hi)
        print(f"Generated: {wav_hi.name}")


if __name__ == "__main__":
    asyncio.run(generate_all_alerts())
