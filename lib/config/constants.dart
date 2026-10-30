/// SatyaSwar Audio and Protocol Constants
/// Specifications strictly matching GEMINI.md and Implementation.md
abstract class AppConstants {
  // Audio Pipeline Specifications
  static const int sampleRate = 16000; // 16,000 Hz
  static const int channels = 1; // Mono
  static const int bitsPerSample = 16; // PCM16
  static const int bytesPerSample = 2;

  // Windowing Mathematics
  static const int windowMs = 3500; // 3.5 seconds
  static const int hopMs = 1750; // 1.75 seconds (50% overlap)
  static const int windowSamples = 56000; // (16000 * 3.5)
  static const int hopSamples = 28000; // (16000 * 1.75)
  static const int windowPayloadBytes = 112000; // (56000 * 2)

  // Binary WebSocket Frame Header Layout
  static const int frameHeaderBytes = 20;
  static const int totalFrameBytes =
      112020; // 20-byte header + 112,000 PCM bytes
  static const int frameVersion = 1;

  // Alerts & Risk Hysteresis
  static const int alertCooldownSeconds = 8;
  static const int stableWindowConfirmCount = 2;

  // Verification Timeouts
  static const int defaultVerificationTimeoutSeconds = 60;

  // Network & WebSockets
  static const Duration connectTimeout = Duration(seconds: 8);
  static const Duration restTimeout = Duration(seconds: 10);
}
