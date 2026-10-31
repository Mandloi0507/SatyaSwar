import 'package:flutter/material.dart';

import '../models/risk_band.dart';
import 'app_colors.dart';

/// Style mapping helper for RiskBand
class RiskStyle {
  final RiskBand band;
  final Color color;
  final Color containerColor;
  final Color borderColor;
  final IconData icon;

  const RiskStyle({
    required this.band,
    required this.color,
    required this.containerColor,
    required this.borderColor,
    required this.icon,
  });

  static RiskStyle of(RiskBand band) {
    switch (band) {
      case RiskBand.low:
        return const RiskStyle(
          band: RiskBand.low,
          color: AppColors.riskLow,
          containerColor: Color(0x1F22C55E), // 12% opacity green
          borderColor: Color(0x4D22C55E), // 30% opacity green
          icon: Icons.shield_rounded,
        );
      case RiskBand.medium:
        return const RiskStyle(
          band: RiskBand.medium,
          color: AppColors.riskMedium,
          containerColor: Color(0x1FF59E0B), // 12% opacity amber
          borderColor: Color(0x4DF59E0B),
          icon: Icons.gpp_maybe_rounded,
        );
      case RiskBand.high:
        return const RiskStyle(
          band: RiskBand.high,
          color: AppColors.riskHigh,
          containerColor: Color(0x1FEF4444), // 12% opacity red
          borderColor: Color(0x4DEF4444),
          icon: Icons.gpp_bad_rounded,
        );
      case RiskBand.unknown:
        return const RiskStyle(
          band: RiskBand.unknown,
          color: AppColors.riskUnknown,
          containerColor: Color(0x1F94A3B8), // 12% opacity slate
          borderColor: Color(0x4D94A3B8),
          icon: Icons.help_outline_rounded,
        );
    }
  }
}
