class AppConfig {
  static const String appName = 'SatyaSwar';
  static const String appTagline = 'Detect. Score. Decide. Verify.';
  static const String appVersion = '1.0.0+1';

  // Configurable server URLs (10.0.2.2 for Android emulator, 127.0.0.1 for desktop/web, or LAN IP)
  static const String defaultServerUrl = String.fromEnvironment(
    'SERVER_URL',
    defaultValue: 'http://10.0.2.2:8000',
  );

  static const String defaultWsUrl = String.fromEnvironment(
    'WS_URL',
    defaultValue: 'ws://10.0.2.2:8000',
  );

  // When true, uses mock authentication and mock audio-analysis streams.
  // Real ML inference through the backend is the default demo mode.
  static const bool defaultUseMocks = bool.fromEnvironment(
    'USE_MOCKS',
    defaultValue: false,
  );
}
