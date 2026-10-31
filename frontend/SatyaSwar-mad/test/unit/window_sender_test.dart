import 'dart:async';
import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:just_audio/just_audio.dart';
import 'package:satyaswar_app/services/window_planner.dart';
import 'package:satyaswar_app/services/window_sender.dart';

void main() {
  group('WindowSender Unit Tests', () {
    late StreamController<Duration> posController;
    late StreamController<PlayerState> stateController;
    late Int16List pcm;
    late WindowPlanner planner;
    late List<int> emittedSeqs;
    late List<Uint8List> emittedFrames;
    late WindowSender sender;

    setUp(() {
      posController = StreamController<Duration>.broadcast();
      stateController = StreamController<PlayerState>.broadcast();
      pcm = Int16List(280000); // 17.5s clip -> 9 windows
      planner = WindowPlanner(totalSamples: pcm.length);
      emittedSeqs = [];
      emittedFrames = [];

      sender = WindowSender(
        positionStream: posController.stream,
        playerStateStream: stateController.stream,
        pcm: pcm,
        planner: planner,
        onFrame: (frame, seq, sentAt) {
          emittedSeqs.add(seq);
          emittedFrames.add(frame);
        },
      );
    });

    tearDown(() async {
      await sender.dispose();
      await posController.close();
      await stateController.close();
    });

    test('does not emit window 0 before position reaches 3500 ms', () async {
      sender.start();

      posController.add(const Duration(milliseconds: 1000));
      posController.add(const Duration(milliseconds: 2000));
      posController.add(const Duration(milliseconds: 3400));
      await Future.delayed(Duration.zero);

      expect(emittedSeqs, isEmpty);
      expect(sender.emittedCount, equals(0));
    });

    test('emits window 0 exactly when position reaches 3500 ms', () async {
      sender.start();

      posController.add(const Duration(milliseconds: 3500));
      await Future.delayed(Duration.zero);

      expect(emittedSeqs, equals([0]));
      expect(sender.emittedCount, equals(1));
    });

    test(
      'emits successive windows in step with playback progression',
      () async {
        sender.start();

        // Reach window 0 end (3500ms)
        posController.add(const Duration(milliseconds: 3500));
        await Future.delayed(Duration.zero);
        expect(emittedSeqs, equals([0]));

        // Ticks before window 1 end (5250ms) do not emit
        posController.add(const Duration(milliseconds: 4000));
        posController.add(const Duration(milliseconds: 5000));
        await Future.delayed(Duration.zero);
        expect(emittedSeqs, equals([0]));

        // Reach window 1 end (5250ms)
        posController.add(const Duration(milliseconds: 5250));
        await Future.delayed(Duration.zero);
        expect(emittedSeqs, equals([0, 1]));

        // Reach window 2 end (7000ms)
        posController.add(const Duration(milliseconds: 7000));
        await Future.delayed(Duration.zero);
        expect(emittedSeqs, equals([0, 1, 2]));
      },
    );

    test('catches up multiple windows if position jumps forward', () async {
      sender.start();

      // Player jumps straight to 7100 ms (covering window 0, 1, 2)
      posController.add(const Duration(milliseconds: 7100));
      await Future.delayed(Duration.zero);

      expect(emittedSeqs, equals([0, 1, 2]));
      expect(sender.emittedCount, equals(3));
    });

    test('flushes all remaining windows when player completes', () async {
      sender.start();

      // Only played up to window 0
      posController.add(const Duration(milliseconds: 3500));
      await Future.delayed(Duration.zero);
      expect(emittedSeqs, equals([0]));

      // Playback completes
      stateController.add(PlayerState(false, ProcessingState.completed));
      await Future.delayed(Duration.zero);

      // All 9 windows (0 to 8) must have been flushed
      expect(emittedSeqs, equals([0, 1, 2, 3, 4, 5, 6, 7, 8]));
      expect(sender.emittedCount, equals(9));
    });

    test('emitted frames have valid 112,020 bytes length', () async {
      sender.start();

      posController.add(const Duration(milliseconds: 3500));
      await Future.delayed(Duration.zero);

      expect(emittedFrames.length, equals(1));
      expect(emittedFrames.first.length, equals(112020));
    });
  });
}
