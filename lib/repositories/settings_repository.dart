import 'package:http/http.dart' as http;
import 'package:shared_preferences/shared_preferences.dart';
import '../utils/logger.dart';

abstract class SettingsRepository {
  Future<String> getServerAddress();
  Future<void> setServerAddress(String address);

  Future<bool> isMockModeEnabled();
  Future<void> setMockMode(bool enabled);

  Future<bool> testBackendConnection(String address);
}

class SettingsRepositoryImpl implements SettingsRepository {
  static const _serverKey = 'satyaswar_server_address';
  static const _mockModeKey = 'satyaswar_mock_mode';

  static const String defaultServerAddress = 'http://10.0.2.2:8000';

  @override
  Future<String> getServerAddress() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_serverKey) ?? defaultServerAddress;
  }

  @override
  Future<void> setServerAddress(String address) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_serverKey, address.trim());
  }

  @override
  Future<bool> isMockModeEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_mockModeKey) ?? true; // Default true until backend is live
  }

  @override
  Future<void> setMockMode(bool enabled) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_mockModeKey, enabled);
  }

  @override
  Future<bool> testBackendConnection(String address) async {
    try {
      final sanitized = address.trim();
      final uri = Uri.parse(sanitized.endsWith('/') ? '${sanitized}health' : '$sanitized/health');
      AppLogger.d('Testing connection to $uri', 'SettingsRepository');
      final res = await http.get(uri).timeout(const Duration(seconds: 4));
      return res.statusCode == 200;
    } catch (e) {
      AppLogger.w('Connection test failed: $e', 'SettingsRepository');
      return false;
    }
  }
}
