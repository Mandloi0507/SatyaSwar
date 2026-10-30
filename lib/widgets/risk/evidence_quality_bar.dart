import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

enum EvidenceLevel { good, limited, poor }

class EvidenceQualityBar extends StatelessWidget {
  final EvidenceLevel level;
  final double usableSpeechSec;

  const EvidenceQualityBar({
    super.key,
    required this.level,
    required this.usableSpeechSec,
  });

  @override
  Widget build(BuildContext context) {
    Color levelColor;
    String levelLabel;
    double progress;

    switch (level) {
      case EvidenceLevel.good:
        levelColor = AppColors.riskLow;
        levelLabel = 'GOOD QUALITY';
        progress = 1.0;
        break;
      case EvidenceLevel.limited:
        levelColor = AppColors.warning;
        levelLabel = 'LIMITED AUDIO';
        progress = 0.55;
        break;
      case EvidenceLevel.poor:
        levelColor = AppColors.danger;
        levelLabel = 'POOR / INSUFFICIENT';
        progress = 0.25;
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Row(
                children: [
                  const Icon(
                    Icons.graphic_eq_rounded,
                    size: 16,
                    color: AppColors.textSecondary,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'Evidence Quality: $levelLabel',
                    style: TextStyle(
                      fontSize: 11,
                      fontWeight: FontWeight.w700,
                      color: levelColor,
                      letterSpacing: 0.5,
                    ),
                  ),
                ],
              ),
              Text(
                '${usableSpeechSec.toStringAsFixed(1)}s speech',
                style: AppTextStyles.caption.copyWith(
                  color: AppColors.textPrimary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          ClipRRect(
            borderRadius: BorderRadius.circular(4),
            child: LinearProgressIndicator(
              value: progress,
              minHeight: 5,
              backgroundColor: AppColors.surfaceHigh,
              valueColor: AlwaysStoppedAnimation<Color>(levelColor),
            ),
          ),
        ],
      ),
    );
  }
}
