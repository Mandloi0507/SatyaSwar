import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';

enum StatusTone { success, warning, danger, neutral, primary }

class StatusChip extends StatelessWidget {
  final String label;
  final IconData? icon;
  final StatusTone tone;
  final bool showDot;

  const StatusChip({
    super.key,
    required this.label,
    this.icon,
    this.tone = StatusTone.neutral,
    this.showDot = true,
  });

  @override
  Widget build(BuildContext context) {
    Color color;
    Color bgColor;

    switch (tone) {
      case StatusTone.success:
        color = AppColors.riskLow;
        bgColor = const Color(0x2222C55E);
        break;
      case StatusTone.warning:
        color = AppColors.warning;
        bgColor = const Color(0x22F59E0B);
        break;
      case StatusTone.danger:
        color = AppColors.danger;
        bgColor = const Color(0x22DC2626);
        break;
      case StatusTone.primary:
        color = AppColors.primaryGlow;
        bgColor = const Color(0x223B82F6);
        break;
      case StatusTone.neutral:
        color = AppColors.textSecondary;
        bgColor = const Color(0x1F94A3B8);
        break;
    }

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: bgColor,
        borderRadius: BorderRadius.circular(20),
        border: Border.all(color: color.withValues(alpha: 0.35), width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          if (showDot) ...[
            Container(
              width: 7,
              height: 7,
              decoration: BoxDecoration(color: color, shape: BoxShape.circle),
            ),
            const SizedBox(width: 6),
          ] else if (icon != null) ...[
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 6),
          ],
          Text(
            label,
            style: AppTextStyles.caption.copyWith(
              color: color,
              fontWeight: FontWeight.w600,
            ),
          ),
        ],
      ),
    );
  }
}
