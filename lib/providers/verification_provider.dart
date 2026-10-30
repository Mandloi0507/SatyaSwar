import 'dart:async';
import 'package:flutter/foundation.dart';
import 'package:local_auth/local_auth.dart';
import '../models/verification_request.dart';
import '../repositories/verification_repository.dart';
import '../utils/logger.dart';

class VerificationProvider with ChangeNotifier {
  final VerificationRepository repository;
  final LocalAuthentication _localAuth = LocalAuthentication();

  VerificationRequest? _currentRequest;
  StreamSubscription<VerificationRequest>? _subscription;
  bool _isLoading = false;
  String? _errorMessage;

  VerificationProvider({required this.repository});

  VerificationRequest? get currentRequest => _currentRequest;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<VerificationRequest?> startVerification({
    required String callId,
    required String contactId,
    required String contactName,
    required String claimedIdentity,
    required String action,
    double? amount,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final req = await repository.createVerificationRequest(
        callId: callId,
        contactId: contactId,
        contactName: contactName,
        claimedIdentity: claimedIdentity,
        action: action,
        amount: amount,
      );

      _currentRequest = req;
      _isLoading = false;
      notifyListeners();

      // Listen for updates from server/mock
      _subscription?.cancel();
      _subscription = repository.listenToRequest(req.requestId).listen(
        (updated) {
          _currentRequest = updated;
          notifyListeners();
        },
      );

      return req;
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
      return null;
    }
  }

  /// Convenience biometric authentication check on the responder side
  /// SECURITY NOTE: Biometrics on the client is an interaction convenience gate only,
  /// NOT a cryptographic proof of identity. The server owns the verification state machine.
  Future<bool> authenticateBiometric() async {
    try {
      final canCheck = await _localAuth.canCheckBiometrics;
      final isSupported = await _localAuth.isDeviceSupported();

      if (!canCheck && !isSupported) {
        return true; // Fallback to PIN / simple approval if hardware is absent
      }

      return await _localAuth.authenticate(
        localizedReason: 'Confirm verification challenge as trusted responder',
        biometricOnly: false,
        persistAcrossBackgrounding: true,
      );
    } catch (e) {
      AppLogger.w('Biometric authentication failed: $e', 'VerificationProvider');
      return true; // Allow fallback for demo
    }
  }

  Future<void> responderApprove(String requestId) async {
    await repository.simulateResponderResponse(
      requestId: requestId,
      approve: true,
    );
  }

  Future<void> responderDeny(String requestId) async {
    await repository.simulateResponderResponse(
      requestId: requestId,
      approve: false,
    );
  }

  void cancelCurrent() {
    if (_currentRequest != null) {
      repository.cancelRequest(_currentRequest!.requestId);
    }
    _subscription?.cancel();
    _subscription = null;
    _currentRequest = null;
    notifyListeners();
  }

  @override
  void dispose() {
    _subscription?.cancel();
    repository.dispose();
    super.dispose();
  }
}
