import 'dart:async';
import 'package:flutter_tts/flutter_tts.dart';
import '../models/risk_band.dart';
import '../utils/logger.dart';
import 'audio_player_service.dart';

class AlertService {
  final AudioPlayerService? audioPlayerService;
  final FlutterTts _tts = FlutterTts();

  RiskBand _lastAlertedBand = RiskBand.low;
  DateTime? _lastAlertTime;
  bool _isSpeaking = false;

  // Configuration
  static const Duration cooldownDuration = Duration(seconds: 10);

  final _alertTextController = StreamController<String>.broadcast();
  Stream<String> get alertTextStream => _alertTextController.stream;

  AlertService({this.audioPlayerService}) {
    _initTts();
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

  /// Evaluates risk band transition with hysteresis and cooldown
  Future<void> evaluateRiskBandChange(RiskBand currentBand) async {
    // 1. Hysteresis rule: only alert on upward severity transition
    final isEscalation = _bandSeverity(currentBand) > _bandSeverity(_lastAlertedBand);

    if (!isEscalation && currentBand != RiskBand.high) {
      return;
    }

    // 2. Cooldown check: prevent alerting repeatedly on every window
    final now = DateTime.now();
    if (_lastAlertTime != null &&
        now.difference(_lastAlertTime!) < cooldownDuration) {
      return;
    }

    _lastAlertedBand = currentBand;
    _lastAlertTime = now;

    // 3. Dispatch alert
    switch (currentBand) {
      case RiskBand.high:
        await _triggerAlert(
          'Warning! High risk synthetic voice detected. Verify caller immediately.',
        );
        break;
      case RiskBand.medium:
        await _triggerAlert(
          'Notice: Acoustic anomaly detected. Voice pitch patterns inconsistent.',
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

  Future<void> _triggerAlert(String message) async {
    if (_isSpeaking) return;
    _isSpeaking = true;
    _alertTextController.add(message);

    AppLogger.d('Triggering spoken alert: $message', 'AlertService');

    try {
      // 1. Duck call audio volume
      if (audioPlayerService != null) {
        await audioPlayerService!.duckVolume(0.2);
      }

      // 2. Speak alert using TTS with proper completion callbacks
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

      // Await real completion callback or safety timeout to ensure volume is always restored
      await completer.future.timeout(
        const Duration(seconds: 5),
        onTimeout: () {
          AppLogger.d('TTS completion callback timed out, proceeding', 'AlertService');
        },
      );
    } catch (e) {
      AppLogger.w('Spoken alert failed: $e', 'AlertService');
    } finally {
      // 3. Always restore original caller volume after the warning
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
  }

  void dispose() {
    _tts.stop();
    _alertTextController.close();
  }
}
