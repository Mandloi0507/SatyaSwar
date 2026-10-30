import 'dart:typed_data';

import 'package:flutter_test/flutter_test.dart';
import 'package:satyaswar_app/services/window_planner.dart';

void main() {
  group('WindowPlanner Unit Tests', () {
    test('calculates correct window and hop samples for 16 kHz mono', () {
      final planner = WindowPlanner(totalSamples: 280000); // 17.5s

      expect(planner.windowSamples, equals(56000)); // 16000 * 3.5
      expect(planner.hopSamples, equals(28000)); // 16000 * 1.75
    });

    test('calculates correct window count for 17.5s demonstration clip', () {
      // 17.5s clip = 280,000 samples
      // Window 0: 0 -> 56,000
      // Window 1: 28,000 -> 84,000
      // Window 2: 56,000 -> 112,000
      // Window 3: 84,000 -> 140,000
      // Window 4: 112,000 -> 168,000
      // Window 5: 140,000 -> 196,000
      // Window 6: 168,000 -> 224,000
      // Window 7: 196,000 -> 252,000
      // Window 8: 224,000 -> 280,000
      // Total = 9 windows
      final planner = WindowPlanner(totalSamples: 280000);
      expect(planner.count, equals(9));
    });

    test('calculates correct window count for 21.0s demonstration clip', () {
      // 21.0s clip = 336,000 samples
      // 1 + (336,000 - 56,000) ~/ 28,000 = 1 + 280,000 ~/ 28,000 = 11 windows
      final planner = WindowPlanner(totalSamples: 336000);
      expect(planner.count, equals(11));
    });

    test(
      'returns 0 windows when total samples are less than 1 window (< 3.5s)',
      () {
        final planner = WindowPlanner(totalSamples: 40000); // 2.5s
        expect(planner.count, equals(0));
      },
    );

    test(
      'calculates exact millisecond offsets for all windows in 17.5s clip',
      () {
        final planner = WindowPlanner(totalSamples: 280000);

        // Window 0: 0ms to 3500ms
        expect(planner.startMsOf(0), equals(0));
        expect(planner.endMsOf(0), equals(3500));

        // Window 1: 1750ms to 5250ms
        expect(planner.startMsOf(1), equals(1750));
        expect(planner.endMsOf(1), equals(5250));

        // Window 2: 3500ms to 7000ms
        expect(planner.startMsOf(2), equals(3500));
        expect(planner.endMsOf(2), equals(7000));

        // Window 8 (Final window): 14000ms to 17500ms
        expect(planner.startMsOf(8), equals(14000));
        expect(planner.endMsOf(8), equals(17500));
      },
    );

    test(
      'sliceOf extracts exact 56000 samples with correct subview values',
      () {
        final samples = Int16List(280000);
        for (var i = 0; i < samples.length; i++) {
          samples[i] = i % 32000;
        }

        final planner = WindowPlanner(totalSamples: samples.length);

        // Test window 0 slice
        final slice0 = planner.sliceOf(samples, 0);
        expect(slice0.length, equals(56000));
        expect(slice0.first, equals(samples[0]));
        expect(slice0.last, equals(samples[55999]));

        // Test window 1 slice (starts at 28,000)
        final slice1 = planner.sliceOf(samples, 1);
        expect(slice1.length, equals(56000));
        expect(slice1.first, equals(samples[28000]));
        expect(slice1.last, equals(samples[28000 + 55999]));

        // Test window 8 slice (starts at 224,000)
        final slice8 = planner.sliceOf(samples, 8);
        expect(slice8.length, equals(56000));
        expect(slice8.first, equals(samples[224000]));
        expect(slice8.last, equals(samples[279999]));
      },
    );

    test('sliceOf throws RangeError for negative or out of bound index', () {
      final samples = Int16List(280000);
      final planner = WindowPlanner(totalSamples: samples.length);

      expect(() => planner.sliceOf(samples, -1), throwsRangeError);
      expect(() => planner.sliceOf(samples, 9), throwsRangeError);
    });
  });
}
