import 'dart:async';
import 'dart:convert';
import 'dart:typed_data';
import 'package:web_socket_channel/io.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import '../models/analysis_result.dart';
import '../utils/logger.dart';
import 'call_analysis_service.dart';

class WebSocketCallAnalysisService implements CallAnalysisService {
  WebSocketChannel? _channel;
  StreamSubscription? _subscription;

  final _connectionStateController =
      StreamController<SocketConnectionState>.broadcast();
  final _analysisResultController =
      StreamController<AnalysisResult>.broadcast();

  SocketConnectionState _state = SocketConnectionState.disconnected;

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

    try {
      final uri = Uri.parse(endpointUrl).replace(
        queryParameters: {
          'call_id': callId,
          'token': ?token,
          ...?initialParameters?.map((k, v) => MapEntry(k, v.toString())),
        },
      );

      AppLogger.d('Opening WebSocket connection to $uri', 'WebSocketService');

      final headers = <String, dynamic>{};
      if (token != null && token.isNotEmpty) {
        headers['Authorization'] = 'Bearer $token';
      }

      _channel = IOWebSocketChannel.connect(
        uri,
        headers: headers.isNotEmpty ? headers : null,
        pingInterval: const Duration(seconds: 15),
      );

      _subscription = _channel!.stream.listen(
        _onMessageReceived,
        onError: (error) {
          AppLogger.e('WebSocket stream error', error, null, 'WebSocketService');
          _setState(SocketConnectionState.error);
        },
        onDone: () {
          AppLogger.d('WebSocket stream closed by server', 'WebSocketService');
          _setState(SocketConnectionState.disconnected);
        },
        cancelOnError: false,
      );

      _setState(SocketConnectionState.connected);
    } catch (e, st) {
      AppLogger.e('WebSocket connection failed', e, st, 'WebSocketService');
      _setState(SocketConnectionState.error);
      rethrow;
    }
  }

  void _onMessageReceived(dynamic message) {
    try {
      if (message is String) {
        final Map<String, dynamic> data = jsonDecode(message);
        final result = AnalysisResult.fromJson(data);
        _analysisResultController.add(result);
      } else if (message is List<int>) {
        final decoded = utf8.decode(message);
        final Map<String, dynamic> data = jsonDecode(decoded);
        final result = AnalysisResult.fromJson(data);
        _analysisResultController.add(result);
      }
    } catch (e, st) {
      AppLogger.e('Failed to parse analysis message', e, st, 'WebSocketService');
    }
  }

  @override
  void sendFrame(Uint8List binaryFrame) {
    if (_state != SocketConnectionState.connected || _channel == null) {
      AppLogger.w(
        'Cannot send frame: WebSocket is not connected ($_state)',
        'WebSocketService',
      );
      return;
    }

    try {
      _channel!.sink.add(binaryFrame);
    } catch (e, st) {
      AppLogger.e('Failed to send binary frame', e, st, 'WebSocketService');
    }
  }

  @override
  Future<void> disconnect() async {
    _setState(SocketConnectionState.disconnected);
    await _subscription?.cancel();
    _subscription = null;
    await _channel?.sink.close();
    _channel = null;
  }

  @override
  void dispose() {
    disconnect();
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
