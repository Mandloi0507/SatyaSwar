import 'dart:async';
import 'package:flutter_tts/flutter_tts.dart';
import 'package:just_audio/just_audio.dart';
import '../models/risk_band.dart';
import '../utils/logger.dart';
import 'audio_player_service.dart';

class AlertService {
  final AudioPlayerService? audioPlayerService;
  final FlutterTts _tts = FlutterTts();
  final AudioPlayer _alertAudioPlayer = AudioPlayer();

  RiskBand _lastAlertedBand = RiskBand.low;
  DateTime? _lastAlertTime;
  bool _isSpeaking = false;
  int _windowsProcessed = 0;

  // Configuration
  static const Duration cooldownDuration = Duration(seconds: 8);

  final _alertTextController = StreamController<String>.broadcast();
  Stream<String> get alertTextStream => _alertTextController.stream;

  AlertService({this.audioPlayerService}) {
    _initTts();
    _alertAudioPlayer.setVolume(1.0);
  }

  Future<void> _initTts() async {
    try {
      await _tts.setLanguage('en-IN');
      await _tts.setPitch(1.0);
      await _tts.setSpeechRate(0.5);
      await _tts.awaitSpeakCompletion(true);
    } catch (e) {
      AppLogger.w('TTS initialization error: $e', 'AlertService');
    }
  }

  /// Evaluates risk band transition with hysteresis, debounce, and cooldown
  Future<void> evaluateRiskBandChange(RiskBand currentBand) async {
    _windowsProcessed++;

    // Guard 1: Ignore first 2 windows (at least 3.5s - 5s) to let the ML model stabilize
    // and avoid false early interruptions
    if (_windowsProcessed < 2) {
      return;
    }

    // Guard 2: If low risk, do not trigger an audio interruption
    if (currentBand == RiskBand.low) {
      _lastAlertedBand = currentBand;
      return;
    }

    // Guard 3: Only alert on upward severity escalation (e.g., low -> medium, medium -> high)
    // or if the band is already High and hasn't alerted yet
    final isEscalation = _bandSeverity(currentBand) > _bandSeverity(_lastAlertedBand);
    if (!isEscalation && currentBand != RiskBand.high) {
      return;
    }

    // Guard 4: If already speaking an alert, never overlap
    if (_isSpeaking) {
      return;
    }

    // Guard 5: Cooldown check: prevent alerting repeatedly on every window
    final now = DateTime.now();
    if (_lastAlertTime != null &&
        now.difference(_lastAlertTime!) < cooldownDuration) {
      return;
    }

    _lastAlertedBand = currentBand;
    _lastAlertTime = now;

    // Dispatch alert with matching bundled alert sound
    switch (currentBand) {
      case RiskBand.high:
        await _triggerAlert(
          'Warning! High risk synthetic voice detected. Verify caller immediately.',
          assetAudioPath: 'assets/audio/alerts/high_en.wav',
        );
        break;
      case RiskBand.medium:
        await _triggerAlert(
          'Notice: Acoustic anomaly detected. Voice pitch patterns inconsistent.',
          assetAudioPath: 'assets/audio/alerts/medium_en.wav',
        );
        break;
      case RiskBand.unknown:
        _alertTextController.add(
          'Notice: Audio evidence insufficient to assess voice integrity.',
        );
        break;
      case RiskBand.low:
        break;
    }
  }

  Future<void> _triggerAlert(String message, {String? assetAudioPath}) async {
    if (_isSpeaking) return;
    _isSpeaking = true;
    _alertTextController.add(message);

    AppLogger.d('Triggering spoken alert: $message (asset: $assetAudioPath)', 'AlertService');

    try {
      // 1. Duck call audio volume smoothly to 15% so warning is loud and clear
      if (audioPlayerService != null) {
        await audioPlayerService!.duckVolume(0.15);
      }

      bool playedWav = false;
      // 2. Play clear high-fidelity bundled alert audio WAV if available
      if (assetAudioPath != null && assetAudioPath.isNotEmpty) {
        try {
          await _alertAudioPlayer.setAsset(assetAudioPath);
          await _alertAudioPlayer.play();
          playedWav = true;
        } catch (wavErr) {
          AppLogger.w('Failed to play alert WAV asset: $wavErr, falling back to TTS', 'AlertService');
        }
      }

      // 3. Fallback to TTS if WAV asset could not be played
      if (!playedWav) {
        final completer = Completer<void>();
        _tts.setCompletionHandler(() {
          if (!completer.isCompleted) completer.complete();
        });
        _tts.setErrorHandler((dynamic msg) {
          AppLogger.w('TTS speech error: $msg', 'AlertService');
          if (!completer.isCompleted) completer.complete();
        });
        _tts.setCancelHandler(() {
          if (!completer.isCompleted) completer.complete();
        });

        await _tts.speak(message);

        await completer.future.timeout(
          const Duration(seconds: 5),
          onTimeout: () {
            AppLogger.d('TTS completion callback timed out, proceeding', 'AlertService');
          },
        );
      }
    } catch (e) {
      AppLogger.w('Spoken alert failed: $e', 'AlertService');
    } finally {
      // 4. Always restore original caller volume after the alert finishes
      if (audioPlayerService != null) {
        await audioPlayerService!.restoreVolume();
      }
      _isSpeaking = false;
    }
  }

  int _bandSeverity(RiskBand band) {
    switch (band) {
      case RiskBand.high:
        return 3;
      case RiskBand.medium:
        return 2;
      case RiskBand.unknown:
        return 1;
      case RiskBand.low:
        return 0;
    }
  }

  void reset() {
    _lastAlertedBand = RiskBand.low;
    _lastAlertTime = null;
    _isSpeaking = false;
    _windowsProcessed = 0;
    _alertAudioPlayer.stop();
  }

  void dispose() {
    _tts.stop();
    _alertAudioPlayer.dispose();
    _alertTextController.close();
  }
}
