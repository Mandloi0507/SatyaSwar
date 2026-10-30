import 'dart:async';
import 'dart:typed_data';
import '../models/analysis_result.dart';
import '../models/risk_band.dart';
import '../utils/logger.dart';
import 'call_analysis_service.dart';

class MockCallAnalysisService implements CallAnalysisService {
  final String scenarioId;
  final _connectionStateController =
      StreamController<SocketConnectionState>.broadcast();
  final _analysisResultController =
      StreamController<AnalysisResult>.broadcast();

  SocketConnectionState _state = SocketConnectionState.disconnected;
  int _receivedFrameCount = 0;

  MockCallAnalysisService({this.scenarioId = 'clone_ceo'});

  @override
  Stream<SocketConnectionState> get connectionStateStream =>
      _connectionStateController.stream;

  @override
  Stream<AnalysisResult> get analysisResultStream =>
      _analysisResultController.stream;

  @override
  SocketConnectionState get currentState => _state;

  @override
  Future<void> connect({
    required String endpointUrl,
    required String callId,
    String? token,
    Map<String, dynamic>? initialParameters,
  }) async {
    _setState(SocketConnectionState.connecting);
    AppLogger.d('Connecting mock socket to $endpointUrl', 'MockCallAnalysis');

    // Simulate network handshake latency
    await Future<void>.delayed(const Duration(milliseconds: 150));
    _receivedFrameCount = 0;
    _setState(SocketConnectionState.connected);
  }

  @override
  void sendFrame(Uint8List binaryFrame) {
    if (_state != SocketConnectionState.connected) return;

    final seq = _receivedFrameCount++;
    AppLogger.d(
      'Mock socket received frame seq $seq (${binaryFrame.length} bytes)',
      'MockCallAnalysis',
    );

    // Simulate backend server analysis latency (280ms)
    Future<void>.delayed(const Duration(milliseconds: 280), () {
      if (_state != SocketConnectionState.connected) return;

      double score;
      RiskBand band;
      double quality = 0.95;
      String? msg;

      switch (scenarioId) {
        case 'clone_ceo':
          if (seq < 2) {
            score = 18.0 + seq * 5;
            band = RiskBand.low;
            msg = 'Acoustic parameters nominal. Natural speech dynamics.';
          } else if (seq < 4) {
            score = 48.0 + (seq - 2) * 8;
            band = RiskBand.medium;
            msg =
                'Acoustic anomaly detected. Suspicious vocal pitch stability.';
          } else {
            score = 84.0 + ((seq * 3) % 11);
            band = RiskBand.high;
            msg = 'WARNING: High probability of synthetic voice cloning.';
          }
          break;

        case 'noisy_call':
        case 'noisy_background':
          score = 38.0 + (seq % 3) * 6;
          band = RiskBand.medium;
          quality = 0.52;
          msg = 'Heavy ambient noise present. Adaptive quality scaling active.';
          break;

        case 'short_insufficient':
          score = 0.0;
          band = RiskBand.unknown;
          quality = 0.18;
          msg = 'Insufficient speech evidence to evaluate voice integrity.';
          break;

        case 'genuine_family':
        default:
          score = 12.0 + (seq % 3) * 3;
          band = RiskBand.low;
          msg = 'No synthetic indicators detected. Natural vocal prosody.';
          break;
      }

      final result = AnalysisResult(
        windowSeq: seq,
        riskScore: score,
        riskBand: band,
        evidenceQuality: quality,
        latencyMs: 280 + (seq * 15) % 80,
        message: msg,
        timestamp: DateTime.now(),
      );

      _analysisResultController.add(result);
    });
  }

  @override
  Future<void> disconnect() async {
    _setState(SocketConnectionState.disconnected);
  }

  @override
  void dispose() {
    _setState(SocketConnectionState.disconnected);
    _connectionStateController.close();
    _analysisResultController.close();
  }

  void _setState(SocketConnectionState newState) {
    _state = newState;
    if (!_connectionStateController.isClosed) {
      _connectionStateController.add(newState);
    }
  }
}
