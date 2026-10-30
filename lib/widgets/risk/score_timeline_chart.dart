import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

class ScoreTimelineChart extends StatelessWidget {
  final List<int> windowScores; // e.g. [20, 24, 75, 82, 88]

  const ScoreTimelineChart({super.key, required this.windowScores});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Row(
                children: [
                  Icon(
                    Icons.show_chart_rounded,
                    size: 16,
                    color: AppColors.primaryGlow,
                  ),
                  SizedBox(width: 6),
                  Text(
                    'Window-by-Window Risk Progression',
                    style: AppTextStyles.caption,
                  ),
                ],
              ),
              Text(
                '${windowScores.length} windows',
                style: const TextStyle(
                  fontSize: 11,
                  color: AppColors.textSecondary,
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),

          // Bar timeline visualization
          SizedBox(
            height: 60,
            child: windowScores.isEmpty
                ? const Center(
                    child: Text(
                      'Awaiting initial 3.5s analysis window...',
                      style: AppTextStyles.caption,
                    ),
                  )
                : Row(
                    crossAxisAlignment: CrossAxisAlignment.end,
                    children: List.generate(windowScores.length, (index) {
                      final score = windowScores[index];
                      Color barColor = AppColors.riskLow;
                      if (score >= 65) {
                        barColor = AppColors.riskHigh;
                      } else if (score >= 35) {
                        barColor = AppColors.riskMedium;
                      }

                      final heightPercent = (score / 100.0).clamp(0.1, 1.0);

                      return Expanded(
                        child: Padding(
                          padding: const EdgeInsets.symmetric(horizontal: 2.5),
                          child: Column(
                            mainAxisAlignment: MainAxisAlignment.end,
                            children: [
                              Text(
                                '$score',
                                style: TextStyle(
                                  fontSize: 8,
                                  fontWeight: FontWeight.w700,
                                  color: barColor,
                                ),
                              ),
                              const SizedBox(height: 2),
                              Container(
                                height: 40 * heightPercent,
                                decoration: BoxDecoration(
                                  color: barColor,
                                  borderRadius: BorderRadius.circular(4),
                                ),
                              ),
                              const SizedBox(height: 4),
                              Text(
                                'W${index + 1}',
                                style: const TextStyle(
                                  fontSize: 8,
                                  color: AppColors.textMuted,
                                ),
                              ),
                            ],
                          ),
                        ),
                      );
                    }),
                  ),
          ),
        ],
      ),
    );
  }
}
