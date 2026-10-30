import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

/// Mandatory Prototype Banner explicitly stating call simulation
/// Defined in GEMINI.md and Section 4 of Implementation.md
class SimulatedBanner extends StatelessWidget {
  const SimulatedBanner({super.key});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      decoration: BoxDecoration(
        color: AppColors.warning.withValues(alpha: 0.16),
        border: Border(
          bottom: BorderSide(
            color: AppColors.warning.withValues(alpha: 0.4),
            width: 1,
          ),
        ),
      ),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          const Icon(
            Icons.warning_amber_rounded,
            size: 16,
            color: AppColors.warning,
          ),
          const SizedBox(width: 8),
          Text(
            'SIMULATED CALL • Demonstrator audio only • Not cellular audio',
            style: AppTextStyles.caption.copyWith(
              color: AppColors.warning,
              fontWeight: FontWeight.w700,
              letterSpacing: 0.5,
            ),
          ),
        ],
      ),
    );
  }
}
