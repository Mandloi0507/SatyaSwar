import 'dart:async';
import 'dart:typed_data';

import 'package:just_audio/just_audio.dart';

import 'audio_frame_builder.dart';
import 'window_planner.dart';

/// Digital Audio Window Synchronizer
/// Synchronizes audio slicing with audible playback so frames are only dispatched
/// when the listener has heard the corresponding audio window (Section 8.6).
class WindowSender {
  final Stream<Duration> positionStream;
  final Stream<PlayerState> playerStateStream;
  final Int16List pcm;
  final WindowPlanner planner;
  final void Function(Uint8List frame, int seq, DateTime sentAt) onFrame;
  final AudioFrameBuilder frameBuilder;

  int _next = 0;
  bool _disposed = false;
  bool _completed = false;
  StreamSubscription<Duration>? _posSub;
  StreamSubscription<PlayerState>? _stateSub;

  WindowSender({
    required this.positionStream,
    required this.playerStateStream,
    required this.pcm,
    required this.planner,
    required this.onFrame,
    this.frameBuilder = const AudioFrameBuilder(),
  });

  /// Index of the next window awaiting emission
  int get nextWindowIndex => _next;

  /// Total windows emitted so far
  int get emittedCount => _next;

  /// Whether playback has finished and windows have completed emission
  bool get isCompleted => _completed;

  /// Whether the sender has been disposed
  bool get isDisposed => _disposed;

  /// Starts listening to playback position and emitting frames as window deadlines are reached
  void start() {
    if (_disposed) return;

    _posSub = positionStream.listen((pos) {
      if (_disposed || _completed) return;
      while (!_disposed &&
          !_completed &&
          _next < planner.count &&
          pos.inMilliseconds >= planner.endMsOf(_next)) {
        _emit(_next++);
      }
    });

    _stateSub = playerStateStream.listen((s) {
      if (_disposed || _completed) return;
      if (s.processingState == ProcessingState.completed) {
        _completed = true;
        // Flush any remaining windows at end of playback
        while (!_disposed && _next < planner.count) {
          _emit(_next++);
        }
      }
    });
  }

  void _emit(int i) {
    if (_disposed) return;
    final now = DateTime.now();
    final slice = planner.sliceOf(pcm, i);
    final frame = frameBuilder.buildFrame(
      seq: i,
      offsetMs: planner.startMsOf(i),
      sendEpochMs: now.millisecondsSinceEpoch,
      pcm: slice,
      isLast: i == planner.count - 1,
    );
    onFrame(frame, i, now);
  }

  /// Cancels stream subscriptions and prevents any subsequent frame emissions
  Future<void> dispose() async {
    _disposed = true;
    await _posSub?.cancel();
    await _stateSub?.cancel();
    _posSub = null;
    _stateSub = null;
  }
}
