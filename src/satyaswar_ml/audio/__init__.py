"""Audio processing modules for SatyaSwar ML subsystem."""
from satyaswar_ml.audio.io import (
    TARGET_SAMPLE_RATE,
    float32_to_pcm16le,
    load_audio,
    load_audio_from_bytes,
    pcm16le_to_float32,
    resample_audio,
)
from satyaswar_ml.audio.telephony import (
    apply_amr_nb,
    apply_g711_alaw,
    apply_g711_ulaw,
    apply_gsm,
    apply_opus_8k,
    apply_telephony_profile,
    get_available_ffmpeg_encoders,
)
from satyaswar_ml.audio.windowing import (
    AudioWindow,
    RingBuffer,
    WindowEmitter,
    prepare_model_input,
)

__all__ = [
    "TARGET_SAMPLE_RATE",
    "AudioWindow",
    "RingBuffer",
    "WindowEmitter",
    "apply_amr_nb",
    "apply_g711_alaw",
    "apply_g711_ulaw",
    "apply_gsm",
    "apply_opus_8k",
    "apply_telephony_profile",
    "float32_to_pcm16le",
    "get_available_ffmpeg_encoders",
    "load_audio",
    "load_audio_from_bytes",
    "pcm16le_to_float32",
    "prepare_model_input",
    "resample_audio",
]
