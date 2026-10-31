import 'dart:async';
import 'dart:typed_data';
import 'package:flutter_test/flutter_test.dart';
import 'package:just_audio/just_audio.dart';
import 'package:satyaswar_app/services/audio_frame_builder.dart';
import 'package:satyaswar_app/services/wav_parser.dart';
import 'package:satyaswar_app/services/window_planner.dart';
import 'package:satyaswar_app/services/window_sender.dart';

void main() {
  group('End-to-End Audio Pipeline Verification Tests', () {
    late Uint8List wavBytes;

    setUp(() {
      // Synthesize a valid 17.5s, 16 kHz, mono, PCM16 WAV byte stream
      // (identical to genuine_01.wav: 280,000 samples)
      const sampleRate = 16000;
      const totalSamples = 280000; // 17.5s
      const dataSize = totalSamples * 2; // 560,000 bytes
      const fileSize = 44 + dataSize;

      final bd = ByteData(fileSize);
      // RIFF header
      bd.setUint8(0, 0x52); // 'R'
      bd.setUint8(1, 0x49); // 'I'
      bd.setUint8(2, 0x46); // 'F'
      bd.setUint8(3, 0x46); // 'F'
      bd.setUint32(4, fileSize - 8, Endian.little);
      bd.setUint8(8, 0x57); // 'W'
      bd.setUint8(9, 0x41); // 'A'
      bd.setUint8(10, 0x56); // 'V'
      bd.setUint8(11, 0x45); // 'E'

      // fmt chunk
      bd.setUint8(12, 0x66); // 'f'
      bd.setUint8(13, 0x6D); // 'm'
      bd.setUint8(14, 0x74); // 't'
      bd.setUint8(15, 0x20); // ' '
      bd.setUint32(16, 16, Endian.little);
      bd.setUint16(20, 1, Endian.little); // PCM format
      bd.setUint16(22, 1, Endian.little); // Mono (1 channel)
      bd.setUint32(24, sampleRate, Endian.little); // 16000 Hz
      bd.setUint32(28, sampleRate * 2, Endian.little); // Byte rate
      bd.setUint16(32, 2, Endian.little); // Block align
      bd.setUint16(34, 16, Endian.little); // Bits per sample (PCM16)

      // data chunk
      bd.setUint8(36, 0x64); // 'd'
      bd.setUint8(37, 0x61); // 'a'
      bd.setUint8(38, 0x74); // 't'
      bd.setUint8(39, 0x61); // 'a'
      bd.setUint32(40, dataSize, Endian.little);

      // Populate samples with known non-zero values
      for (var i = 0; i < totalSamples; i++) {
        bd.setInt16(44 + (i * 2), (i % 1000) - 500, Endian.little);
      }

      wavBytes = bd.buffer.asUint8List();
    });

    test('1. Validates WAV parsing for 16 kHz mono PCM16 specifications', () {
      final wavData = WavParser.parse(wavBytes);
      expect(wavData.sampleRate, equals(16000));
      expect(wavData.channels, equals(1));
      expect(wavData.bitsPerSample, equals(16));
      expect(wavData.totalSamples, equals(280000));
      expect(wavData.durationMs, equals(17500));
    });

    test('2. Validates WindowPlanner: 3.5s window, 1.75s hop, exactly 9 windows', () {
      final wavData = WavParser.parse(wavBytes);
      final planner = WindowPlanner(totalSamples: wavData.totalSamples);

      expect(planner.windowMs, equals(3500));
      expect(planner.hopMs, equals(1750));
      expect(planner.windowSamples, equals(56000));
      expect(planner.hopSamples, equals(28000));
      expect(planner.windowSamples * 2, equals(112000));
      expect(planner.hopSamples * 2, equals(56000));

      expect(planner.count, equals(9));

      // Window boundary verification
      expect(planner.startMsOf(0), equals(0));
      expect(planner.endMsOf(0), equals(3500));

      expect(planner.startMsOf(1), equals(1750));
      expect(planner.endMsOf(1), equals(5250));

      expect(planner.startMsOf(8), equals(14000));
      expect(planner.endMsOf(8), equals(17500));
    });

    test('3. Validates WindowSender: position-gated emission during playback progression', () async {
      final wavData = WavParser.parse(wavBytes);
      final planner = WindowPlanner(totalSamples: wavData.totalSamples);

      final positionController = StreamController<Duration>.broadcast();
      final playerStateController = StreamController<PlayerState>.broadcast();

      final List<int> emittedSequences = [];
      final List<Uint8List> emittedFrames = [];

      final sender = WindowSender(
        positionStream: positionController.stream,
        playerStateStream: playerStateController.stream,
        pcm: wavData.samples,
        planner: planner,
        frameBuilder: const AudioFrameBuilder(),
        onFrame: (frame, seq, timestamp) {
          emittedSequences.add(seq);
          emittedFrames.add(frame);
        },
      );

      sender.start();

      // Playback begins: 0 to 3000ms -> 0 windows emitted
      positionController.add(const Duration(milliseconds: 500));
      positionController.add(const Duration(milliseconds: 2000));
      positionController.add(const Duration(milliseconds: 3400));
      await Future<void>.delayed(Duration.zero);
      expect(emittedSequences.isEmpty, isTrue, reason: 'No window should be emitted before endMsOf(0) = 3500ms');

      // Playback reaches 3500ms -> Window 0 emitted
      positionController.add(const Duration(milliseconds: 3500));
      await Future<void>.delayed(Duration.zero);
      expect(emittedSequences, equals([0]));

      // Playback advances to 5250ms -> Window 1 emitted
      positionController.add(const Duration(milliseconds: 5250));
      await Future<void>.delayed(Duration.zero);
      expect(emittedSequences, equals([0, 1]));

      // Playback advances to 7000ms -> Window 2 emitted
      positionController.add(const Duration(milliseconds: 7000));
      await Future<void>.delayed(Duration.zero);
      expect(emittedSequences, equals([0, 1, 2]));

      // Advance through remainder of playback
      for (var ms = 8750; ms <= 17500; ms += 1750) {
        positionController.add(Duration(milliseconds: ms));
      }
      await Future<void>.delayed(Duration.zero);

      expect(emittedSequences.length, equals(9));
      expect(emittedSequences, equals([0, 1, 2, 3, 4, 5, 6, 7, 8]));

      // Validate every emitted frame structure:
      // Exact frame length: 112,020 bytes (20 byte header + 112,000 byte payload)
      const strategy = Proposed20ByteHeaderStrategy();
      for (var i = 0; i < emittedFrames.length; i++) {
        final frame = emittedFrames[i];
        expect(frame.length, equals(112020));

        final bd = ByteData.sublistView(frame);
        final header = strategy.parseHeader(bd);

        // Header fields
        expect(header['version'], equals(1));
        expect(header['seq'], equals(i));
        expect(header['offsetMs'], equals(planner.startMsOf(i)));
        expect(header['isLast'], equals(i == 8));
      }

      sender.dispose();
      await positionController.close();
      await playerStateController.close();
    });

    test('4. Validates frame builder strategy modularity for backend protocol updates', () {
      const builder = AudioFrameBuilder();
      expect(builder.headerStrategy.headerLengthBytes, equals(20));
      expect(builder.headerStrategy, isA<Proposed20ByteHeaderStrategy>());

      // Custom mock header strategy (demonstrating modular decoupling for Member 2)
      final dummySamples = Int16List(56000);
      final customStrategy = _Mock16ByteHeaderStrategy();
      final customBuilder = AudioFrameBuilder(headerStrategy: customStrategy);

      expect(customBuilder.headerStrategy.headerLengthBytes, equals(16));
      final frame = customBuilder.buildFrame(
        seq: 0,
        offsetMs: 0,
        sendEpochMs: 123456789,
        pcm: dummySamples,
        isLast: false,
      );

      // 16 bytes header + 112,000 bytes PCM = 112,016 bytes
      expect(frame.length, equals(112016));
      expect(frame[0], equals(0xAA));
      expect(frame[1], equals(0xBB));
    });
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
    targetByteData.setUint8(0, 0xAA);
    targetByteData.setUint8(1, 0xBB);
    targetByteData.setUint16(2, 2, Endian.big);
    targetByteData.setUint32(4, seq, Endian.big);
    targetByteData.setUint32(8, offsetMs, Endian.big);
    targetByteData.setUint32(12, sendEpochMs & 0xFFFFFFFF, Endian.big);
  }

  @override
  Map<String, dynamic> parseHeader(ByteData byteData) {
    return {
      'magic': 0xAABB,
      'seq': byteData.getUint32(4, Endian.big),
      'offsetMs': byteData.getUint32(8, Endian.big),
    };
  }
}
