import 'dart:typed_data';

/// Encapsulates parsed PCM16 audio data from a WAV container
class WavData {
  final int sampleRate;
  final int channels;
  final int bitsPerSample;
  final Int16List samples; // mono PCM16 samples

  const WavData({
    required this.sampleRate,
    required this.channels,
    required this.bitsPerSample,
    required this.samples,
  });

  /// Duration in milliseconds calculated from sample count
  int get durationMs => samples.length * 1000 ~/ sampleRate;

  /// Total sample count
  int get totalSamples => samples.length;

  /// Total PCM payload size in bytes
  int get byteLength => samples.length * 2;
}

/// RIFF/WAVE Chunk Walker and Audio Format Validator
/// Defined in Section 8.3 of Implementation.md
abstract class WavParser {
  /// Parses raw byte data of a WAV file.
  /// Throws [FormatException] if file is corrupted or does not strictly match 16 kHz mono PCM16.
  static WavData parse(Uint8List bytes) {
    if (bytes.length < 44) {
      throw const FormatException(
        'File too small to be a valid WAV file (minimum 44 bytes)',
      );
    }

    final bd = ByteData.sublistView(bytes);

    // Validate RIFF header
    if (_tag(bytes, 0) != 'RIFF' || _tag(bytes, 8) != 'WAVE') {
      throw const FormatException('Not a valid RIFF/WAVE file container');
    }

    int? formatCode;
    int? channels;
    int? sampleRate;
    int? bitsPerSample;
    int? dataStart;
    int? dataLength;

    var offset = 12;
    while (offset + 8 <= bytes.length) {
      final chunkId = _tag(bytes, offset);
      final chunkSize = bd.getUint32(offset + 4, Endian.little);
      final body = offset + 8;

      if (chunkId == 'fmt ') {
        formatCode = bd.getUint16(body, Endian.little);
        channels = bd.getUint16(body + 2, Endian.little);
        sampleRate = bd.getUint32(body + 4, Endian.little);
        bitsPerSample = bd.getUint16(body + 14, Endian.little);
      } else if (chunkId == 'data') {
        dataStart = body;
        dataLength = chunkSize.clamp(0, bytes.length - body);
        break; // Reached data chunk
      }

      // Chunks are 2-byte word aligned in RIFF
      offset = body + chunkSize + (chunkSize.isOdd ? 1 : 0);
    }

    // Strict validation against SatyaSwar audio requirements
    if (formatCode != 1) {
      throw FormatException(
        'WAV must be uncompressed PCM (format 1, got $formatCode)',
      );
    }
    if (sampleRate != 16000) {
      throw FormatException(
        'Sample rate must be exactly 16,000 Hz, got $sampleRate Hz',
      );
    }
    if (channels != 1) {
      throw FormatException(
        'Audio must be mono (1 channel), got $channels channels',
      );
    }
    if (bitsPerSample != 16) {
      throw FormatException(
        'Bit depth must be 16-bit PCM, got $bitsPerSample-bit',
      );
    }
    if (dataStart == null || dataLength == null) {
      throw const FormatException('No valid data chunk found in WAV file');
    }

    final numSamples = dataLength ~/ 2;
    final samples = Int16List(numSamples);

    for (var i = 0; i < numSamples; i++) {
      samples[i] = bd.getInt16(dataStart + i * 2, Endian.little);
    }

    return WavData(
      sampleRate: sampleRate!,
      channels: channels!,
      bitsPerSample: bitsPerSample!,
      samples: samples,
    );
  }

  static String _tag(Uint8List bytes, int offset) {
    return String.fromCharCodes(bytes.sublist(offset, offset + 4));
  }
}
