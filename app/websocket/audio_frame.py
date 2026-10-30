"""
SatyaSwar - Audio Frame Decoder and Validator
Member 2: Backend, Infrastructure, Database and Security

Decodes and validates binary audio window frames transmitted by the Flutter mobile client.
Seamlessly supports both Member 1's proposed 20-byte LE header and Member 2's 12-byte BE header,
as well as raw PCM payloads.
"""

from dataclasses import dataclass
import struct
from typing import Optional

# Standard window payload size for 3.5 seconds at 16 kHz mono signed 16-bit PCM
EXPECTED_PCM_BYTES = 112000  # 3.5 * 16000 * 2
MEMBER1_HEADER_LEN = 20
MEMBER2_HEADER_LEN = 12


class InvalidAudioFrameError(Exception):
    """Raised when an incoming binary frame fails layout, length, or sequence validation."""

    def __init__(self, message: str, code: int = 4413):
        super().__init__(message)
        self.message = message
        self.code = code


@dataclass
class ParsedAudioFrame:
    """Represents a validated audio window frame ready for ML inference."""

    seq: int
    offset_ms: int
    timestamp_ms: int
    is_last: bool
    pcm_bytes: bytes


def parse_audio_frame(
    raw_bytes: bytes,
    expected_pcm_size: int = EXPECTED_PCM_BYTES,
    last_seq: Optional[int] = None,
) -> ParsedAudioFrame:
    """
    Parses and validates a raw binary audio frame received over WebSocket.

    Supported formats:
    1. Member 1 format (20-byte LE header + PCM payload):
       - 0: version (uint8)
       - 1: flags (uint8, bit 0 = is_last)
       - 2-3: reserved (uint16 LE)
       - 4-7: seq (uint32 LE)
       - 8-11: offset_ms (uint32 LE)
       - 12-19: send_epoch_ms (uint64 LE)
       - 20-end: PCM16 LE payload
    2. Member 2 format (12-byte BE header + PCM payload):
       - 0-3: seq (uint32 BE)
       - 4-11: client_capture_ms (uint64 BE)
       - 12-end: PCM16 payload
    3. Raw PCM payload (exact PCM length):
       - seq defaults to last_seq + 1 (or 0)

    Raises:
        InvalidAudioFrameError: If payload length is incorrect, sequence is out of order,
                                or header is malformed.
    """
    total_len = len(raw_bytes)

    # Strategy 1: Member 1 format (20-byte header + PCM)
    if total_len == MEMBER1_HEADER_LEN + expected_pcm_size:
        try:
            version, flags, _, seq, offset_ms, send_epoch_ms = struct.unpack(
                "<BBHIIQ", raw_bytes[:MEMBER1_HEADER_LEN]
            )
            is_last = bool(flags & 0x01)
            pcm = raw_bytes[MEMBER1_HEADER_LEN:]
            parsed = ParsedAudioFrame(
                seq=seq,
                offset_ms=offset_ms,
                timestamp_ms=send_epoch_ms,
                is_last=is_last,
                pcm_bytes=pcm,
            )
        except struct.error as e:
            raise InvalidAudioFrameError(f"Malformed 20-byte audio frame header: {e}") from e

    # Strategy 2: Member 2 format (12-byte header + PCM)
    elif total_len == MEMBER2_HEADER_LEN + expected_pcm_size:
        try:
            seq, timestamp_ms = struct.unpack(">IQ", raw_bytes[:MEMBER2_HEADER_LEN])
            pcm = raw_bytes[MEMBER2_HEADER_LEN:]
            parsed = ParsedAudioFrame(
                seq=seq,
                offset_ms=seq * 1750,  # approximate from hop interval
                timestamp_ms=timestamp_ms,
                is_last=False,
                pcm_bytes=pcm,
            )
        except struct.error as e:
            raise InvalidAudioFrameError(f"Malformed 12-byte audio frame header: {e}") from e

    # Strategy 3: Raw PCM payload (no header)
    elif total_len == expected_pcm_size:
        next_seq = 0 if last_seq is None else last_seq + 1
        parsed = ParsedAudioFrame(
            seq=next_seq,
            offset_ms=next_seq * 1750,
            timestamp_ms=0,
            is_last=False,
            pcm_bytes=raw_bytes,
        )

    else:
        raise InvalidAudioFrameError(
            f"Invalid audio frame size: received {total_len} bytes; expected "
            f"{expected_pcm_size} (raw), {MEMBER2_HEADER_LEN + expected_pcm_size} (12-byte header), "
            f"or {MEMBER1_HEADER_LEN + expected_pcm_size} (20-byte header)"
        )

    # Validate sequence monotonicity
    if last_seq is not None:
        if parsed.seq <= last_seq:
            raise InvalidAudioFrameError(
                f"Duplicate or out-of-order audio frame: received seq {parsed.seq}, last was {last_seq}",
                code=4413,
            )

    return parsed
