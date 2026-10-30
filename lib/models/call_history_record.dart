import 'risk_band.dart';

/// Scores-only audit record of a past call session
/// PRIVACY GUARANTEE: Never stores raw audio bytes or speech transcripts
class CallHistoryRecord {
  final String id;
  final String callerName;
  final String callerNumber;
  final DateTime timestamp;
  final int durationSeconds;
  final int peakRiskScore; // 0-100
  final RiskBand peakRiskBand;
  final double evidenceQuality; // 0.0-1.0
  final String verificationStatus; // 'confirmed', 'denied', 'unverified', 'not_requested'
  final String finalOutcome; // 'Likely genuine', 'High risk synthetic', 'Insufficient evidence'
  final List<int> timelineScores;

  const CallHistoryRecord({
    required this.id,
    required this.callerName,
    required this.callerNumber,
    required this.timestamp,
    required this.durationSeconds,
    required this.peakRiskScore,
    required this.peakRiskBand,
    required this.evidenceQuality,
    required this.verificationStatus,
    required this.finalOutcome,
    required this.timelineScores,
  });

  Map<String, dynamic> toJson() => {
        'id': id,
        'callerName': callerName,
        'callerNumber': callerNumber,
        'timestamp': timestamp.toIso8601String(),
        'durationSeconds': durationSeconds,
        'peakRiskScore': peakRiskScore,
        'peakRiskBand': peakRiskBand.name,
        'evidenceQuality': evidenceQuality,
        'verificationStatus': verificationStatus,
        'finalOutcome': finalOutcome,
        'timelineScores': timelineScores,
      };

  factory CallHistoryRecord.fromJson(Map<String, dynamic> json) {
    final rawBand = json['peakRiskBand'] as String? ?? 'low';
    final band = RiskBand.fromString(rawBand);

    final rawScores = json['timelineScores'] as List<dynamic>? ?? [];

    return CallHistoryRecord(
      id: json['id'] as String,
      callerName: json['callerName'] as String,
      callerNumber: json['callerNumber'] as String,
      timestamp: json['timestamp'] != null
          ? DateTime.tryParse(json['timestamp'] as String) ?? DateTime.now()
          : DateTime.now(),
      durationSeconds: (json['durationSeconds'] as num?)?.toInt() ?? 0,
      peakRiskScore: (json['peakRiskScore'] as num?)?.toInt() ?? 0,
      peakRiskBand: band,
      evidenceQuality: (json['evidenceQuality'] as num?)?.toDouble() ?? 1.0,
      verificationStatus:
          json['verificationStatus'] as String? ?? 'not_requested',
      finalOutcome: json['finalOutcome'] as String? ?? 'Unknown',
      timelineScores: rawScores.map((e) => (e as num).toInt()).toList(),
    );
  }
}
