import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:satyaswar_app/services/audio_frame_builder.dart';

void main() {
  group('AudioFrameBuilder Unit Tests', () {
    const builder = AudioFrameBuilder();

    test(
      'builds binary frame with exact 112,020 bytes for 56,000 PCM samples',
      () {
        final pcm = Int16List(56000);
        for (var i = 0; i < pcm.length; i++) {
          pcm[i] = (i * 2) - 1000;
        }

        final frame = builder.buildFrame(
          seq: 3,
          offsetMs: 5250,
          sendEpochMs: 1729864200000,
          pcm: pcm,
          isLast: false,
        );

        // 20-byte header + (56000 samples * 2 bytes/sample) = 112,020 bytes
        expect(frame.length, equals(112020));

        final bd = ByteData.sublistView(frame);
        final strategy = const Proposed20ByteHeaderStrategy();
        final header = strategy.parseHeader(bd);

        expect(header['version'], equals(1));
        expect(header['isLast'], isFalse);
        expect(header['reserved'], equals(0));
        expect(header['seq'], equals(3));
        expect(header['offsetMs'], equals(5250));
        expect(header['sendEpochMs'], equals(1729864200000));
      },
    );

    test('sets isLast flag correctly in flags byte (bit 0)', () {
      final pcm = Int16List(56000);
      final frame = builder.buildFrame(
        seq: 8,
        offsetMs: 14000,
        sendEpochMs: 1729864210000,
        pcm: pcm,
        isLast: true,
      );

      final bd = ByteData.sublistView(frame);
      final strategy = const Proposed20ByteHeaderStrategy();
      final header = strategy.parseHeader(bd);

      expect(header['isLast'], isTrue);
      expect(header['seq'], equals(8));
    });

    test('extractPcm perfectly recovers original PCM16 samples', () {
      final pcm = Int16List(56000);
      pcm[0] = 32767; // max positive int16
      pcm[1] = -32768; // max negative int16
      pcm[28000] = 12345;
      pcm[55999] = -4321;

      final frame = builder.buildFrame(
        seq: 0,
        offsetMs: 0,
        sendEpochMs: 1729864000000,
        pcm: pcm,
      );

      final extracted = builder.extractPcm(frame);

      expect(extracted.length, equals(56000));
      expect(extracted[0], equals(32767));
      expect(extracted[1], equals(-32768));
      expect(extracted[28000], equals(12345));
      expect(extracted[55999], equals(-4321));
    });

    test(
      'allows custom header strategy for modular backend protocol changes',
      () {
        // Test demonstrating modularity: if backend requests a different header format
        final customStrategy = _Mock16ByteHeaderStrategy();
        final customBuilder = AudioFrameBuilder(headerStrategy: customStrategy);
        final pcm = Int16List(100);

        final frame = customBuilder.buildFrame(
          seq: 1,
          offsetMs: 1750,
          sendEpochMs: 1000,
          pcm: pcm,
        );

        // 16 bytes header + 200 bytes pcm = 216 bytes
        expect(frame.length, equals(216));
      },
    );
  });
}

class _Mock16ByteHeaderStrategy implements AudioFrameHeaderStrategy {
  @override
  int get headerLengthBytes => 16;

  @override
  void writeHeader({
    required ByteData targetByteData,
    required int seq,
    required int offsetMs,
    required int sendEpochMs,
    required bool isLast,
  }) {
    targetByteData.setUint32(0, seq, Endian.little);
    targetByteData.setUint32(4, offsetMs, Endian.little);
    targetByteData.setUint64(8, sendEpochMs, Endian.little);
  }

  @override
  Map<String, dynamic> parseHeader(ByteData byteData) {
    return {
      'seq': byteData.getUint32(0, Endian.little),
      'offsetMs': byteData.getUint32(4, Endian.little),
      'sendEpochMs': byteData.getUint64(8, Endian.little),
    };
  }
}
