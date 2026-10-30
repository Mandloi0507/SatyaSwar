import 'dart:typed_data';

/// Window Mathematics & Slicing Planner
/// Defined in Section 8.4 of Implementation.md
/// Window: 3.5s (56,000 samples / 112,000 bytes)
/// Hop: 1.75s (28,000 samples / 56,000 bytes) -> 50% overlap
class WindowPlanner {
  final int totalSamples;
  final int sampleRate;
  final int windowMs;
  final int hopMs;

  const WindowPlanner({
    required this.totalSamples,
    this.sampleRate = 16000,
    this.windowMs = 3500,
    this.hopMs = 1750,
  });

  /// Samples per full window: 16000 * 3.5 = 56000
  int get windowSamples => sampleRate * windowMs ~/ 1000;

  /// Samples per window hop: 16000 * 1.75 = 28000
  int get hopSamples => sampleRate * hopMs ~/ 1000;

  /// Total number of complete windows available in the sample sequence
  int get count {
    if (totalSamples < windowSamples) return 0;
    return 1 + (totalSamples - windowSamples) ~/ hopSamples;
  }

  /// Start sample index for window [i]
  int startSampleOf(int i) => i * hopSamples;

  /// End sample index (exclusive) for window [i]
  int endSampleOf(int i) => startSampleOf(i) + windowSamples;

  /// Start time offset in milliseconds for window [i]
  int startMsOf(int i) => startSampleOf(i) * 1000 ~/ sampleRate;

  /// End time offset in milliseconds for window [i]
  /// Playback position must reach this timestamp before window [i] is emitted.
  int endMsOf(int i) => endSampleOf(i) * 1000 ~/ sampleRate;

  /// Slices window [i] from raw mono PCM16 data without memory re-allocation
  Int16List sliceOf(Int16List pcm, int i) {
    if (i < 0 || i >= count) {
      throw RangeError.range(
        i,
        0,
        count - 1,
        'windowIndex',
        'Window index out of valid range',
      );
    }
    final start = startSampleOf(i);
    final end = start + windowSamples;
    return Int16List.sublistView(pcm, start, end);
  }
}
