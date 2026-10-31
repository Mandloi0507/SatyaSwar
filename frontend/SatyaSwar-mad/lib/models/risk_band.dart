/// Voice Risk Bands returned by backend and visualized in the UI
enum RiskBand {
  low,
  medium,
  high,
  unknown;

  static RiskBand fromString(String? value) {
    if (value == null) return RiskBand.unknown;
    switch (value.toLowerCase().trim()) {
      case 'low':
        return RiskBand.low;
      case 'medium':
        return RiskBand.medium;
      case 'high':
        return RiskBand.high;
      case 'unknown':
      case 'insufficient':
      case 'insufficient_evidence':
      default:
        return RiskBand.unknown;
    }
  }

  String get key => name;

  String get shortLabel {
    switch (this) {
      case RiskBand.low:
        return 'LOW RISK';
      case RiskBand.medium:
        return 'MEDIUM RISK';
      case RiskBand.high:
        return 'HIGH RISK';
      case RiskBand.unknown:
        return 'INSUFFICIENT';
    }
  }

  String get fullTitle {
    switch (this) {
      case RiskBand.low:
        return 'No synthetic indicators detected';
      case RiskBand.medium:
        return 'Suspicious voice characteristics';
      case RiskBand.high:
        return 'High probability of synthetic speech';
      case RiskBand.unknown:
        return 'Insufficient evidence to classify';
    }
  }

  String get advice {
    switch (this) {
      case RiskBand.low:
        return 'Voice appears natural. Note: low risk is not proof of identity. Independent verification recommended before sensitive actions.';
      case RiskBand.medium:
        return 'Acoustic anomalies detected. Exercise caution and verify identity before sharing sensitive information.';
      case RiskBand.high:
        return 'Synthetic voice patterns detected. Do not transfer funds or share credentials. Verify caller through trusted contact.';
      case RiskBand.unknown:
        return 'Acoustic sample too short or noisy to reliably evaluate. Refusing to guess.';
    }
  }
}
