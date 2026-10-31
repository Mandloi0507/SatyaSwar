import 'dart:math';

import 'package:flutter/material.dart';

import '../../models/risk_band.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../theme/risk_style.dart';

/// Semi-circular animated risk gauge
/// Labelled "Risk Index" - never "probability of fake" (Implementation.md Section 6.4)
class RiskMeter extends StatelessWidget {
  final double? riskIndex; // 0 to 100
  final RiskBand band;
  final bool isAnalysing;

  const RiskMeter({
    super.key,
    required this.riskIndex,
    required this.band,
    this.isAnalysing = false,
  });

  @override
  Widget build(BuildContext context) {
    final style = RiskStyle.of(band);
    final displayScore = riskIndex != null
        ? riskIndex!.round().toString()
        : '--';

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: 200,
          height: 120,
          child: CustomPaint(
            painter: _GaugePainter(score: riskIndex ?? 0, color: style.color),
            child: Align(
              alignment: Alignment.bottomCenter,
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(
                    displayScore,
                    style: AppTextStyles.displayRisk.copyWith(
                      color: style.color,
                      fontSize: 48,
                    ),
                  ),
                  const Text(
                    'RISK INDEX',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      letterSpacing: 1.5,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          isAnalysing ? 'Analysing initial window...' : band.shortLabel,
          style: TextStyle(
            fontSize: 13,
            fontWeight: FontWeight.w700,
            color: style.color,
            letterSpacing: 0.8,
          ),
        ),
      ],
    );
  }
}

class _GaugePainter extends CustomPainter {
  final double score; // 0 to 100
  final Color color;

  _GaugePainter({required this.score, required this.color});

  @override
  void paint(Canvas canvas, Size size) {
    final center = Offset(size.width / 2, size.height);
    final radius = size.width / 2 - 14;

    const startAngle = pi;
    const sweepAngle = pi;

    // Background track
    final trackPaint = Paint()
      ..color = AppColors.surfaceHigh
      ..style = PaintingStyle.stroke
      ..strokeWidth = 14
      ..strokeCap = StrokeCap.round;

    canvas.drawArc(
      Rect.fromCircle(center: center, radius: radius),
      startAngle,
      sweepAngle,
      false,
      trackPaint,
    );

    // Active progress arc
    final activeSweep = (score.clamp(0, 100) / 100) * pi;
    if (activeSweep > 0) {
      final activePaint = Paint()
        ..color = color
        ..style = PaintingStyle.stroke
        ..strokeWidth = 14
        ..strokeCap = StrokeCap.round;

      canvas.drawArc(
        Rect.fromCircle(center: center, radius: radius),
        startAngle,
        activeSweep,
        false,
        activePaint,
      );
    }
  }

  @override
  bool shouldRepaint(covariant _GaugePainter oldDelegate) {
    return oldDelegate.score != score || oldDelegate.color != color;
  }
}
