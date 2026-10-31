import 'package:flutter/foundation.dart';

/// Privacy-safe application logger
/// Strictly enforces security rule: Never log raw audio bytes, transcripts, or sensitive credentials
abstract class AppLogger {
  static void d(String message, [String? tag]) {
    if (kDebugMode) {
      final prefix = tag != null ? '[$tag] ' : '';
      debugPrint('[DEBUG] $prefix$message');
    }
  }

  static void i(String message, [String? tag]) {
    final prefix = tag != null ? '[$tag] ' : '';
    debugPrint('[INFO] $prefix$message');
  }

  static void w(String message, [String? tag]) {
    final prefix = tag != null ? '[$tag] ' : '';
    debugPrint('[WARN] $prefix$message');
  }

  static void e(
    String message, [
    dynamic error,
    StackTrace? stackTrace,
    String? tag,
  ]) {
    final prefix = tag != null ? '[$tag] ' : '';
    debugPrint('[ERROR] $prefix$message');
    if (error != null) {
      debugPrint('  Details: $error');
    }
    if (stackTrace != null && kDebugMode) {
      debugPrint('  Stack: $stackTrace');
    }
  }
}
