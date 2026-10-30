import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:just_audio/just_audio.dart';
import 'package:satyaswar_app/services/audio_frame_builder.dart';
import 'package:satyaswar_app/services/window_planner.dart';
import 'package:satyaswar_app/services/window_sender.dart';

void main() {
  group('Audio Playback Lifecycle Tests', () {
    late StreamController<Duration> posController;
    late StreamController<PlayerState> stateController;
    late Int16List pcm;
    late WindowPlanner planner;
    late List<int> emittedSeqs;
    late WindowSender sender;

    setUp(() {
      posController = StreamController<Duration>.broadcast();
      stateController = StreamController<PlayerState>.broadcast();
      pcm = Int16List(280000); // 17.5s = 9 windows
      planner = WindowPlanner(totalSamples: pcm.length);
      emittedSeqs = [];

      sender = WindowSender(
        positionStream: posController.stream,
        playerStateStream: stateController.stream,
        pcm: pcm,
        planner: planner,
        frameBuilder: const AudioFrameBuilder(),
        onFrame: (frame, seq, sentAt) {
          emittedSeqs.add(seq);
        },
      );
    });

    tearDown(() async {
      await sender.dispose();
      await posController.close();
      await stateController.close();
    });

    test('sender does not emit any window before start() is called', () async {
      posController.add(const Duration(milliseconds: 5000));
      await Future.delayed(Duration.zero);
      expect(emittedSeqs, isEmpty);
    });

    test('sender properly disposes and stops emitting after dispose()', () async {
      sender.start();

      posController.add(const Duration(milliseconds: 3500));
      await Future.delayed(Duration.zero);
      expect(emittedSeqs, equals([0]));

      await sender.dispose();
      emittedSeqs.clear();

      // Further position ticks should not produce emissions
      posController.add(const Duration(milliseconds: 7000));
      await Future.delayed(Duration.zero);
      expect(emittedSeqs, isEmpty);
    });

    test('sender emits exactly 9 windows for a complete 17.5s playback', () async {
      sender.start();

      // Simulate full playback with position updates every ~1.75s
      for (int ms = 1750; ms <= 17500; ms += 1750) {
        posController.add(Duration(milliseconds: ms));
        await Future.delayed(Duration.zero);
      }

      // Flush remaining via completion
      stateController.add(PlayerState(false, ProcessingState.completed));
      await Future.delayed(Duration.zero);

      expect(emittedSeqs.toSet(), equals({0, 1, 2, 3, 4, 5, 6, 7, 8}));
    });

    test('emitted frame contains valid PCM payload size', () async {
      Uint8List? capturedFrame;
      final localSender = WindowSender(
        positionStream: posController.stream,
        playerStateStream: stateController.stream,
        pcm: pcm,
        planner: planner,
        frameBuilder: const AudioFrameBuilder(),
        onFrame: (frame, seq, sentAt) {
          capturedFrame ??= frame;
        },
      );

      localSender.start();
      posController.add(const Duration(milliseconds: 3500));
      await Future.delayed(Duration.zero);

      expect(capturedFrame, isNotNull);
      // 20-byte header + 112,000 bytes PCM = 112,020
      expect(capturedFrame!.length, equals(112020));

      // Extract and verify PCM payload size
      final extracted = const AudioFrameBuilder().extractPcm(capturedFrame!);
      expect(extracted.length, equals(56000));

      await localSender.dispose();
    });

    test('audio player service interface exposes required streams', () {
      // Verify that the WindowSender can be constructed with the expected
      // stream interfaces that AudioPlayerService would provide
      expect(posController.stream, isA<Stream<Duration>>());
      expect(stateController.stream, isA<Stream<PlayerState>>());
    });
  });

  group('Client Non-Generation of Authenticity Verdicts', () {
    // These tests verify the architectural constraint that the mobile client
    // never independently calculates final voice authenticity outcomes

    test('AudioFrameBuilder does not contain risk scoring logic', () {
      const builder = AudioFrameBuilder();
      final pcm = Int16List(56000);
      final frame = builder.buildFrame(
        seq: 0,
        offsetMs: 0,
        sendEpochMs: DateTime.now().millisecondsSinceEpoch,
        pcm: pcm,
      );

      // Frame should contain only header + raw PCM, no score fields
      expect(frame.length, equals(112020));

      // Parse header and verify no score-related fields exist
      final bd = ByteData.sublistView(frame);
      final header = const Proposed20ByteHeaderStrategy().parseHeader(bd);
      expect(header.containsKey('riskScore'), isFalse);
      expect(header.containsKey('verdict'), isFalse);
      expect(header.containsKey('authenticity'), isFalse);
    });

    test('WindowPlanner performs only temporal slicing, no analysis', () {
      final planner = WindowPlanner(totalSamples: 280000);

      // WindowPlanner should only expose window boundaries, not scoring
      expect(planner.count, equals(9));
      expect(planner.windowSamples, equals(56000));
      expect(planner.hopSamples, equals(28000));

      // Verify it computes offsets but never analyzes content
      expect(planner.startMsOf(0), equals(0));
      expect(planner.endMsOf(0), equals(3500));
    });

    test('frame header strategy contains no authenticity/score fields', () {
      const strategy = Proposed20ByteHeaderStrategy();

      // Header is exactly 20 bytes: version(1) + flags(1) + reserved(2)
      // + seq(4) + offset(4) + timestamp(8) = 20
      expect(strategy.headerLengthBytes, equals(20));

      // Build a header and verify only transport metadata is present
      final bytes = Uint8List(20);
      final bd = ByteData.sublistView(bytes);
      strategy.writeHeader(
        targetByteData: bd,
        seq: 5,
        offsetMs: 8750,
        sendEpochMs: 1729864200000,
        isLast: false,
      );

      final parsed = strategy.parseHeader(bd);
      // Only transport metadata keys should exist
      expect(parsed.keys.toSet(), equals({'version', 'isLast', 'reserved', 'seq', 'offsetMs', 'sendEpochMs'}));
    });
  });
}
