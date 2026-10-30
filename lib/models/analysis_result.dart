import 'risk_band.dart';

/// Real-time speech window risk analysis score returned by backend
class AnalysisResult {
  final int windowSeq;
  final double riskScore; // 0.0 to 100.0
  final RiskBand riskBand;
  final double evidenceQuality; // 0.0 to 1.0
  final int latencyMs;
  final String? message;
  final Map<String, dynamic>? spectralDetails;
  final DateTime timestamp;

  const AnalysisResult({
    required this.windowSeq,
    required this.riskScore,
    required this.riskBand,
    required this.evidenceQuality,
    required this.latencyMs,
    this.message,
    this.spectralDetails,
    required this.timestamp,
  });

  factory AnalysisResult.fromJson(Map<String, dynamic> json) {
    final rawScore = (json['risk_score'] ?? json['score'] ?? 0).toDouble();
    final rawBand = json['risk_band'] ?? json['band'] ?? 'low';
    final rawQuality =
        (json['evidence_quality'] ?? json['quality'] ?? 1.0).toDouble();

    final band = RiskBand.fromString(rawBand.toString());

    return AnalysisResult(
      windowSeq: (json['window_seq'] ?? json['seq'] ?? 0) as int,
      riskScore: rawScore.clamp(0.0, 100.0),
      riskBand: band,
      evidenceQuality: rawQuality.clamp(0.0, 1.0),
      latencyMs: (json['latency_ms'] ?? 300) as int,
      message: json['message'] as String?,
      spectralDetails: json['spectral_details'] as Map<String, dynamic>?,
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'] as String) ?? DateTime.now()
          : DateTime.now(),
    );
  }

  Map<String, dynamic> toJson() => {
        'window_seq': windowSeq,
        'risk_score': riskScore,
        'risk_band': riskBand.name,
        'evidence_quality': evidenceQuality,
        'latency_ms': latencyMs,
        'message': message,
        'spectral_details': spectralDetails,
        'timestamp': timestamp.toIso8601String(),
      };
}
