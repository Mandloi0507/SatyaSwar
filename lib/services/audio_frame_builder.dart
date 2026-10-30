import 'dart:typed_data';

/// Abstract Strategy for Binary Frame Header
/// Modular design: The 20-byte header is currently a PROPOSAL awaiting backend confirmation.
/// Making this modular ensures the header layout can be easily updated once Member 2 confirms the protocol.
abstract class AudioFrameHeaderStrategy {
  int get headerLengthBytes;

  void writeHeader({
    required ByteData targetByteData,
    required int seq,
    required int offsetMs,
    required int sendEpochMs,
    required bool isLast,
  });

  Map<String, dynamic> parseHeader(ByteData byteData);
}

/// Proposed 20-byte little-endian header layout (Implementation.md Section 8.5)
/// [PROPOSAL - NOT YET FINALIZED BY BACKEND]
/// Bytes 0: version (uint8)
/// Bytes 1: flags (uint8, bit 0 = isLast)
/// Bytes 2-3: reserved (uint16, 0)
/// Bytes 4-7: seq (uint32)
/// Bytes 8-11: offsetMs (uint32)
/// Bytes 12-19: sendEpochMs (uint64)
class Proposed20ByteHeaderStrategy implements AudioFrameHeaderStrategy {
  const Proposed20ByteHeaderStrategy();

  @override
  int get headerLengthBytes => 20;

  @override
  void writeHeader({
    required ByteData targetByteData,
    required int seq,
    required int offsetMs,
    required int sendEpochMs,
    required bool isLast,
  }) {
    targetByteData.setUint8(0, 1); // Version = 1
    targetByteData.setUint8(1, isLast ? 1 : 0); // Flags: bit 0 = isLast
    targetByteData.setUint16(2, 0, Endian.little); // Reserved
    targetByteData.setUint32(4, seq, Endian.little); // Sequence number
    targetByteData.setUint32(8, offsetMs, Endian.little); // Offset in audio
    targetByteData.setUint64(
      12,
      sendEpochMs,
      Endian.little,
    ); // Client send timestamp
  }

  @override
  Map<String, dynamic> parseHeader(ByteData byteData) {
    return {
      'version': byteData.getUint8(0),
      'isLast': (byteData.getUint8(1) & 0x01) == 1,
      'reserved': byteData.getUint16(2, Endian.little),
      'seq': byteData.getUint32(4, Endian.little),
      'offsetMs': byteData.getUint32(8, Endian.little),
      'sendEpochMs': byteData.getUint64(12, Endian.little),
    };
  }
}

/// Modular Audio Frame Builder
class AudioFrameBuilder {
  final AudioFrameHeaderStrategy headerStrategy;

  const AudioFrameBuilder({
    this.headerStrategy = const Proposed20ByteHeaderStrategy(),
  });

  /// Constructs a complete binary frame containing the header and PCM16 samples
  Uint8List buildFrame({
    required int seq,
    required int offsetMs,
    required int sendEpochMs,
    required Int16List pcm,
    bool isLast = false,
  }) {
    final headerLen = headerStrategy.headerLengthBytes;
    final pcmBytesLength = pcm.length * 2;
    final frame = Uint8List(headerLen + pcmBytesLength);
    final bd = ByteData.sublistView(frame);

    // 1. Write header using modular strategy
    headerStrategy.writeHeader(
      targetByteData: bd,
      seq: seq,
      offsetMs: offsetMs,
      sendEpochMs: sendEpochMs,
      isLast: isLast,
    );

    // 2. Write PCM16 samples (little-endian)
    for (var i = 0; i < pcm.length; i++) {
      bd.setInt16(headerLen + i * 2, pcm[i], Endian.little);
    }

    return frame;
  }

  /// Extracts PCM samples from a binary frame
  Int16List extractPcm(Uint8List frame) {
    final headerLen = headerStrategy.headerLengthBytes;
    final pcmByteLength = frame.length - headerLen;
    final numSamples = pcmByteLength ~/ 2;
    final bd = ByteData.sublistView(frame, headerLen);
    final samples = Int16List(numSamples);

    for (var i = 0; i < numSamples; i++) {
      samples[i] = bd.getInt16(i * 2, Endian.little);
    }

    return samples;
  }
}
