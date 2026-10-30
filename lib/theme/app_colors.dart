import 'package:flutter/material.dart';

/// SatyaSwar Design System - Core Color Palette
/// As defined in GEMINI.md and Implementation.md
abstract class AppColors {
  // Monochromatic Dark Foundation
  static const Color background = Color(0xFF0A0F1C);
  static const Color surface = Color(0xFF121A2B);
  static const Color surfaceHigh = Color(0xFF1A2438);
  static const Color border = Color(0xFF26334D);

  // Primary Cybersecurity Blue Accents
  static const Color primary = Color(0xFF3B82F6);
  static const Color primaryDeep = Color(0xFF1D4ED8);
  static const Color primaryGlow = Color(0xFF60A5FA);

  // Typography Tokens
  static const Color textPrimary = Color(0xFFF8FAFC);
  static const Color textSecondary = Color(0xFF94A3B8);
  static const Color textMuted = Color(0xFF64748B);

  // Voice Risk Bands
  static const Color riskLow = Color(0xFF22C55E);
  static const Color riskMedium = Color(0xFFF59E0B);
  static const Color riskHigh = Color(0xFFEF4444);
  static const Color riskUnknown = Color(0xFF94A3B8);

  // Verification & Status States
  static const Color success = Color(0xFF16A34A);
  static const Color warning = Color(0xFFF59E0B);
  static const Color danger = Color(0xFFDC2626);

  // Selective Glassmorphism Tokens
  static const Color glass = Color(0x14FFFFFF); // 8% white opacity
  static const Color glassBorder = Color(0x1FFFFFFF); // 12% white opacity
  static const Color overlayScrim = Color(0xB3000000); // 70% black overlay
}
