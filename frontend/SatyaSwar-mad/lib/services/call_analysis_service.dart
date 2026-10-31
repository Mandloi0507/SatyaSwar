import 'dart:async';
import 'dart:typed_data';
import '../models/analysis_result.dart';

enum SocketConnectionState {
  disconnected,
  connecting,
  connected,
  reconnecting,
  error,
}

abstract class CallAnalysisService {
  Stream<SocketConnectionState> get connectionStateStream;
  Stream<AnalysisResult> get analysisResultStream;
  SocketConnectionState get currentState;

  Future<void> connect({
    required String endpointUrl,
    required String callId,
    String? token,
    Map<String, dynamic>? initialParameters,
  });

  void sendFrame(Uint8List binaryFrame);

  Future<void> disconnect();

  void dispose();
}
