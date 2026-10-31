import 'package:flutter/material.dart';

import '../../models/risk_band.dart';
import '../../theme/app_text_styles.dart';
import '../../theme/risk_style.dart';

class RiskBandBadge extends StatelessWidget {
  final RiskBand band;
  final bool compact;

  const RiskBandBadge({super.key, required this.band, this.compact = false});

  @override
  Widget build(BuildContext context) {
    final style = RiskStyle.of(band);

    return Container(
      padding: EdgeInsets.symmetric(
        horizontal: compact ? 8 : 12,
        vertical: compact ? 4 : 6,
      ),
      decoration: BoxDecoration(
        color: style.containerColor,
        borderRadius: BorderRadius.circular(10),
        border: Border.all(color: style.borderColor, width: 1),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(style.icon, size: compact ? 14 : 16, color: style.color),
          const SizedBox(width: 6),
          Text(
            band.shortLabel,
            style: AppTextStyles.badge.copyWith(
              color: style.color,
              fontSize: compact ? 10 : 12,
            ),
          ),
        ],
      ),
    );
  }
}
