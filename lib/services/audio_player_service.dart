import 'package:just_audio/just_audio.dart';

import '../utils/logger.dart';

/// Audio Player Service wrapping just_audio
/// Manages playback of bundled WAV clips and volume ducking for spoken alerts
class AudioPlayerService {
  final AudioPlayer _player;
  double _normalVolume = 1.0;

  AudioPlayerService({AudioPlayer? player}) : _player = player ?? AudioPlayer();

  AudioPlayer get rawPlayer => _player;

  Stream<Duration> get positionStream => _player.positionStream;
  Stream<PlayerState> get playerStateStream => _player.playerStateStream;
  Stream<Duration?> get durationStream => _player.durationStream;

  Duration get position => _player.position;
  Duration? get duration => _player.duration;
  bool get isPlaying => _player.playing;

  /// Loads an audio asset from Flutter rootBundle
  Future<Duration?> loadAsset(String assetPath) async {
    try {
      AppLogger.d('Loading audio asset: $assetPath', 'AudioPlayerService');
      final dur = await _player.setAsset(assetPath);
      return dur;
    } catch (e, st) {
      AppLogger.e(
        'Failed to load audio asset: $assetPath',
        e,
        st,
        'AudioPlayerService',
      );
      rethrow;
    }
  }

  /// Starts playback
  Future<void> play() async {
    await _player.play();
  }

  /// Pauses playback
  Future<void> pause() async {
    await _player.pause();
  }

  /// Stops playback and resets position
  Future<void> stop() async {
    await _player.stop();
  }

  /// Sets normal playback volume (0.0 to 1.0)
  Future<void> setVolume(double volume) async {
    _normalVolume = volume.clamp(0.0, 1.0);
    await _player.setVolume(_normalVolume);
  }

  /// Lowers call audio volume during spoken alerts (ducking)
  Future<void> duckVolume([double duckFactor = 0.2]) async {
    final target = (_normalVolume * duckFactor).clamp(0.0, 1.0);
    await _player.setVolume(target);
  }

  /// Restores normal playback volume after alert finishes
  Future<void> restoreVolume() async {
    await _player.setVolume(_normalVolume);
  }

  /// Releases audio player resources
  Future<void> dispose() async {
    await _player.dispose();
  }
}
