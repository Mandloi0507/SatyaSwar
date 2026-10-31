import 'dart:async';
import 'dart:math';
import '../models/verification_request.dart';
import '../utils/logger.dart';

abstract class VerificationRepository {
  Stream<VerificationRequest> listenToRequest(String requestId);

  Future<VerificationRequest> createVerificationRequest({
    required String callId,
    required String contactId,
    required String contactName,
    required String claimedIdentity,
    required String action,
    double? amount,
  });

  Future<void> simulateResponderResponse({
    required String requestId,
    required bool approve,
  });

  Future<void> cancelRequest(String requestId);
  void dispose();
}

class MockVerificationRepository implements VerificationRepository {
  final Map<String, VerificationRequest> _requests = {};
  final Map<String, StreamController<VerificationRequest>> _controllers = {};
  Timer? _countdownTimer;

  @override
  Stream<VerificationRequest> listenToRequest(String requestId) {
    if (!_controllers.containsKey(requestId)) {
      _controllers[requestId] = StreamController<VerificationRequest>.broadcast();
    }
    final req = _requests[requestId];
    if (req != null) {
      Timer.run(() {
        if (_controllers[requestId]?.isClosed == false) {
          _controllers[requestId]!.add(req);
        }
      });
    }
    return _controllers[requestId]!.stream;
  }

  @override
  Future<VerificationRequest> createVerificationRequest({
    required String callId,
    required String contactId,
    required String contactName,
    required String claimedIdentity,
    required String action,
    double? amount,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 250));

    final requestId = 'req_${DateTime.now().millisecondsSinceEpoch}';
    final matchCode = _generateMatchCode();
    final now = DateTime.now();
    final expiresAt = now.add(const Duration(seconds: 45));

    final request = VerificationRequest(
      requestId: requestId,
      callId: callId,
      contactId: contactId,
      contactName: contactName,
      claimedIdentity: claimedIdentity,
      action: action,
      amount: amount,
      matchCode: matchCode,
      status: VerificationStatus.pending,
      createdAt: now,
      expiresAt: expiresAt,
    );

    _requests[requestId] = request;

    // Start expiry monitor timer
    _startExpiryMonitor(requestId, expiresAt);

    AppLogger.d(
      'Created verification request $requestId, matchCode: $matchCode',
      'VerificationRepository',
    );

    return request;
  }

  void _startExpiryMonitor(String requestId, DateTime expiresAt) {
    _countdownTimer?.cancel();
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      final req = _requests[requestId];
      if (req == null || !req.isPending) {
        timer.cancel();
        return;
      }

      if (DateTime.now().isAfter(expiresAt)) {
        timer.cancel();
        final expiredReq = req.copyWith(
          status: VerificationStatus.expired,
          resolvedAt: DateTime.now(),
        );
        _requests[requestId] = expiredReq;
        _controllers[requestId]?.add(expiredReq);
        AppLogger.d('Verification request $requestId expired', 'VerificationRepository');
      } else {
        // Emit updated request state to keep subscribers synchronized
        _controllers[requestId]?.add(req);
      }
    });
  }

  @override
  Future<void> simulateResponderResponse({
    required String requestId,
    required bool approve,
  }) async {
    final req = _requests[requestId];
    if (req == null || !req.isPending) return;

    _countdownTimer?.cancel();
    final updated = req.copyWith(
      status: approve ? VerificationStatus.confirmed : VerificationStatus.denied,
      resolvedAt: DateTime.now(),
    );

    _requests[requestId] = updated;
    _controllers[requestId]?.add(updated);

    AppLogger.d(
      'Simulated responder resolution for $requestId: ${updated.status.name}',
      'VerificationRepository',
    );
  }

  @override
  Future<void> cancelRequest(String requestId) async {
    _countdownTimer?.cancel();
    final req = _requests[requestId];
    if (req != null && req.isPending) {
      final updated = req.copyWith(
        status: VerificationStatus.denied,
        resolvedAt: DateTime.now(),
      );
      _requests[requestId] = updated;
      _controllers[requestId]?.add(updated);
    }
  }

  String _generateMatchCode() {
    const chars = '23456789ABCDEFGHJKLMNPQRSTUVWXYZ';
    final random = Random();
    return List.generate(6, (_) => chars[random.nextInt(chars.length)]).join();
  }

  @override
  void dispose() {
    _countdownTimer?.cancel();
    for (final controller in _controllers.values) {
      controller.close();
    }
    _controllers.clear();
  }
}
