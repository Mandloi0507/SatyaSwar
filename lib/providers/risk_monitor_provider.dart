import 'dart:async';
import 'package:flutter/foundation.dart';
import '../models/analysis_result.dart';
import '../models/risk_band.dart';
import '../services/alert_service.dart';
import '../services/call_analysis_service.dart';
import '../services/mock_call_analysis_service.dart';
import '../services/websocket_call_analysis_service.dart';
import '../utils/logger.dart';

class RiskMonitorProvider with ChangeNotifier {
  CallAnalysisService? _analysisService;
  StreamSubscription<AnalysisResult>? _resultSubscription;
  StreamSubscription<SocketConnectionState>? _stateSubscription;
  AlertService? _alertService;

  double _currentScore = 14.0;
  RiskBand _currentBand = RiskBand.low;
  double _evidenceQuality = 1.0;
  double _peakScore = 14.0;
  final List<int> _timelineScores = [];
  int _windowsAnalysed = 0;
  int _lastLatencyMs = 280;
  String _latestAlertMessage =
      'Acoustic parameters nominal. Analysing speech windows.';
  SocketConnectionState _connectionState = SocketConnectionState.disconnected;

  double get currentScore => _currentScore;
  RiskBand get currentBand => _currentBand;
  double get evidenceQuality => _evidenceQuality;
  double get peakScore => _peakScore;
  List<int> get timelineScores => List.unmodifiable(_timelineScores);
  int get windowsAnalysed => _windowsAnalysed;
  double get speechSeconds => (_windowsAnalysed * 1.75).clamp(0.0, 60.0);
  int get lastLatencyMs => _lastLatencyMs;
  String get latestAlertMessage => _latestAlertMessage;
  SocketConnectionState get connectionState => _connectionState;

  void attachAlertService(AlertService alertService) {
    _alertService = alertService;
  }

  Future<void> startAnalysis({
    required String callId,
    required String scenarioId,
    required bool isMockMode,
    required String serverBaseAddress,
    String? token,
  }) async {
    reset();

    if (isMockMode) {
      _analysisService = MockCallAnalysisService(scenarioId: scenarioId);
    } else {
      _analysisService = WebSocketCallAnalysisService();
    }

    _stateSubscription = _analysisService!.connectionStateStream.listen((state) {
      _connectionState = state;
      notifyListeners();
    });

    _resultSubscription = _analysisService!.analysisResultStream.listen(
      _onAnalysisResultReceived,
    );

    final wsUrl = _formatWsUrl(serverBaseAddress, callId);
    await _analysisService!.connect(
      endpointUrl: wsUrl,
      callId: callId,
      token: token,
    );
  }

  void ingestFrame(Uint8List binaryFrame) {
    _analysisService?.sendFrame(binaryFrame);
  }

  void _onAnalysisResultReceived(AnalysisResult result) {
    _currentScore = result.riskScore;
    _currentBand = result.riskBand;
    _evidenceQuality = result.evidenceQuality;
    _lastLatencyMs = result.latencyMs;
    _windowsAnalysed = result.windowSeq + 1;

    if (_currentScore > _peakScore) {
      _peakScore = _currentScore;
    }

    _timelineScores.add(_currentScore.round());

    if (result.message != null && result.message!.isNotEmpty) {
      _latestAlertMessage = result.message!;
    } else {
      _latestAlertMessage = _defaultMessageForBand(_currentBand);
    }

    notifyListeners();

    // Trigger spoken alert check through AlertService
    _alertService?.evaluateRiskBandChange(_currentBand);

    AppLogger.d(
      'Analysis Window ${result.windowSeq}: score=${result.riskScore.round()}, band=${result.riskBand.name}, latency=${result.latencyMs}ms',
      'RiskMonitorProvider',
    );
  }

  String _defaultMessageForBand(RiskBand band) {
    switch (band) {
      case RiskBand.high:
        return 'WARNING: High probability of synthetic voice cloning.';
      case RiskBand.medium:
        return 'Acoustic anomaly detected. Suspicious vocal pitch stability.';
      case RiskBand.unknown:
        return 'Audio evidence insufficient to evaluate voice integrity.';
      case RiskBand.low:
        return 'No synthetic indicators detected. Natural vocal prosody.';
    }
  }

  String _formatWsUrl(String baseHttpUrl, String callId) {
    var wsUrl = baseHttpUrl.replaceFirst('http://', 'ws://').replaceFirst('https://', 'wss://');
    if (!wsUrl.endsWith('/')) wsUrl += '/';
    return '${wsUrl}ws/call/$callId';
  }

  void reset() {
    _currentScore = 14.0;
    _currentBand = RiskBand.low;
    _evidenceQuality = 1.0;
    _peakScore = 14.0;
    _timelineScores.clear();
    _windowsAnalysed = 0;
    _lastLatencyMs = 280;
    _latestAlertMessage =
        'Acoustic parameters nominal. Analysing speech windows.';
    _connectionState = SocketConnectionState.disconnected;
    _alertService?.reset();
    notifyListeners();
  }

  Future<void> stopAnalysis() async {
    await _resultSubscription?.cancel();
    _resultSubscription = null;
    await _stateSubscription?.cancel();
    _stateSubscription = null;
    await _analysisService?.disconnect();
    _analysisService?.dispose();
    _analysisService = null;
    _connectionState = SocketConnectionState.disconnected;
    notifyListeners();
  }

  @override
  void dispose() {
    stopAnalysis();
    super.dispose();
  }
}
