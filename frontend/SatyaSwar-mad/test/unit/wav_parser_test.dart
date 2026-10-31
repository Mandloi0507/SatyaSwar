import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:satyaswar_app/services/wav_parser.dart';

void main() {
  group('WavParser Unit Tests', () {
    Uint8List createWavBytes({
      int sampleRate = 16000,
      int channels = 1,
      int bitsPerSample = 16,
      int formatCode = 1,
      int numSamples = 16000, // 1.0 second
      String riffTag = 'RIFF',
      String waveTag = 'WAVE',
    }) {
      final dataSize = numSamples * channels * (bitsPerSample ~/ 8);
      final fileSize = 36 + dataSize;
      final bytes = Uint8List(44 + dataSize);
      final bd = ByteData.sublistView(bytes);

      bytes.setRange(0, 4, riffTag.codeUnits);
      bd.setUint32(4, fileSize, Endian.little);
      bytes.setRange(8, 12, waveTag.codeUnits);

      bytes.setRange(12, 16, 'fmt '.codeUnits);
      bd.setUint32(16, 16, Endian.little);
      bd.setUint16(20, formatCode, Endian.little);
      bd.setUint16(22, channels, Endian.little);
      bd.setUint32(24, sampleRate, Endian.little);
      bd.setUint32(
        28,
        sampleRate * channels * (bitsPerSample ~/ 8),
        Endian.little,
      );
      bd.setUint16(32, channels * (bitsPerSample ~/ 8), Endian.little);
      bd.setUint16(34, bitsPerSample, Endian.little);

      bytes.setRange(36, 40, 'data'.codeUnits);
      bd.setUint32(40, dataSize, Endian.little);

      // Fill sample data
      for (var i = 0; i < numSamples; i++) {
        bd.setInt16(44 + i * 2, i % 1000, Endian.little);
      }

      return bytes;
    }

    test('successfully parses valid 16 kHz mono PCM16 WAV', () {
      final wavBytes = createWavBytes(numSamples: 16000);
      final wavData = WavParser.parse(wavBytes);

      expect(wavData.sampleRate, equals(16000));
      expect(wavData.channels, equals(1));
      expect(wavData.bitsPerSample, equals(16));
      expect(wavData.totalSamples, equals(16000));
      expect(wavData.durationMs, equals(1000));
      expect(wavData.byteLength, equals(32000));
    });

    test('throws FormatException when bytes length < 44', () {
      final corruptedBytes = Uint8List(30);
      expect(() => WavParser.parse(corruptedBytes), throwsFormatException);
    });

    test('throws FormatException when not a RIFF/WAVE container', () {
      final wavBytes = createWavBytes(riffTag: 'NOPE');
      expect(() => WavParser.parse(wavBytes), throwsFormatException);
    });

    test('throws FormatException when sample rate is not 16000 Hz', () {
      final wavBytes = createWavBytes(sampleRate: 44100);
      expect(
        () => WavParser.parse(wavBytes),
        throwsA(
          isA<FormatException>().having(
            (e) => e.message,
            'message',
            contains('16,000 Hz'),
          ),
        ),
      );
    });

    test(
      'throws FormatException when audio has more than 1 channel (stereo)',
      () {
        final wavBytes = createWavBytes(channels: 2);
        expect(
          () => WavParser.parse(wavBytes),
          throwsA(
            isA<FormatException>().having(
              (e) => e.message,
              'message',
              contains('mono'),
            ),
          ),
        );
      },
    );

    test('throws FormatException when bit depth is not 16-bit', () {
      final wavBytes = createWavBytes(bitsPerSample: 24);
      expect(
        () => WavParser.parse(wavBytes),
        throwsA(
          isA<FormatException>().having(
            (e) => e.message,
            'message',
            contains('16-bit'),
          ),
        ),
      );
    });

    test('throws FormatException when audio format is not uncompressed PCM (format 1)', () {
      final wavBytes = createWavBytes(formatCode: 3); // IEEE float
      expect(
        () => WavParser.parse(wavBytes),
        throwsA(
          isA<FormatException>().having(
            (e) => e.message,
            'message',
            contains('uncompressed PCM'),
          ),
        ),
      );
    });
  });
}
