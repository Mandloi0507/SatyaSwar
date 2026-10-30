class AppConfig {
  static const String appName = 'SatyaSwar';
  static const String appTagline = 'Detect. Score. Decide. Verify.';
  static const String appVersion = '1.0.0+1';

  // Configurable server URLs
  static const String defaultServerUrl = String.fromEnvironment(
    'SERVER_URL',
    defaultValue: 'http://192.168.43.10:8000',
  );

  static const String defaultWsUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'ws://192.168.43.10:8000',
  );

  // When true, uses mock authentication and mock audio-analysis streams
  static const bool defaultUseMocks = bool.fromEnvironment(
    'USE_MOCKS',
    defaultValue: true,
  );
}
