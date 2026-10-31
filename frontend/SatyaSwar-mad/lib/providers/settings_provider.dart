import 'package:flutter/foundation.dart';
import '../repositories/settings_repository.dart';

class SettingsProvider with ChangeNotifier {
  final SettingsRepository settingsRepository;

  String _serverAddress = SettingsRepositoryImpl.defaultServerAddress;
  bool _isMockMode = true;
  bool _isTestingConnection = false;
  bool? _lastConnectionStatus;

  SettingsProvider({required this.settingsRepository}) {
    _loadSettings();
  }

  String get serverAddress => _serverAddress;
  bool get isMockMode => _isMockMode;
  bool get isTestingConnection => _isTestingConnection;
  bool? get lastConnectionStatus => _lastConnectionStatus;

  Future<void> _loadSettings() async {
    _serverAddress = await settingsRepository.getServerAddress();
    _isMockMode = await settingsRepository.isMockModeEnabled();
    notifyListeners();
  }

  Future<void> updateServerAddress(String newAddress) async {
    _serverAddress = newAddress.trim();
    await settingsRepository.setServerAddress(_serverAddress);
    _lastConnectionStatus = null;
    notifyListeners();
  }

  Future<void> toggleMockMode(bool enabled) async {
    _isMockMode = enabled;
    await settingsRepository.setMockMode(enabled);
    notifyListeners();
  }

  Future<bool> testConnection() async {
    _isTestingConnection = true;
    _lastConnectionStatus = null;
    notifyListeners();

    final success = await settingsRepository.testBackendConnection(_serverAddress);
    _isTestingConnection = false;
    _lastConnectionStatus = success;
    notifyListeners();
    return success;
  }
}
