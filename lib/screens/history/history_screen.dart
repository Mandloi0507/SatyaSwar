import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../models/risk_band.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/risk_band_badge.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final historyItems = [
      {
        'id': 'call_8f21a',
        'date': 'Today, 03:15 PM',
        'claimedContact': 'Rakesh Sir (CEO)',
        'peakRiskIndex': 91,
        'peakBand': RiskBand.high,
        'verificationStatus': 'Denied',
        'outcome': 'Likely Impersonation',
      },
      {
        'id': 'call_4e10b',
        'date': 'Today, 01:10 PM',
        'claimedContact': 'Priyanka Sharma',
        'peakRiskIndex': 12,
        'peakBand': RiskBand.low,
        'verificationStatus': 'Confirmed',
        'outcome': 'Genuine Caller',
      },
      {
        'id': 'call_1a99c',
        'date': 'Yesterday, 06:45 PM',
        'claimedContact': 'Bank Officer',
        'peakRiskIndex': 35,
        'peakBand': RiskBand.unknown,
        'verificationStatus': 'Unverified',
        'outcome': 'Insufficient Audio Evidence',
      },
    ];

    return AppScaffold(
      appBar: AppBar(title: const Text('Call History')),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        children: [
          Container(
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: AppColors.surfaceHigh,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: AppColors.border),
            ),
            child: const Row(
              children: [
                Icon(
                  Icons.lock_clock_outlined,
                  size: 18,
                  color: AppColors.primaryGlow,
                ),
                SizedBox(width: 10),
                Expanded(
                  child: Text(
                    'Scores-only storage: Audio streams and transcripts are discarded in compliance with privacy mandates.',
                    style: TextStyle(
                      fontSize: 11,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          ...historyItems.map((item) => _buildHistoryCard(context, item)),
        ],
      ),
    );
  }

  Widget _buildHistoryCard(BuildContext context, Map<String, dynamic> item) {
    final band = item['peakBand'] as RiskBand;
    final isDanger = band == RiskBand.high;

    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Material(
        color: AppColors.surface,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(18),
          side: BorderSide(
            color: isDanger
                ? AppColors.danger.withValues(alpha: 0.3)
                : AppColors.border,
          ),
        ),
        child: ListTile(
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 8,
          ),
          onTap: () => context.push('/history/${item['id']}', extra: item),
          title: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                item['claimedContact'] as String,
                style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
              ),
              RiskBandBadge(band: band, compact: true),
            ],
          ),
          subtitle: Padding(
            padding: const EdgeInsets.only(top: 6.0),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '${item['date']} • Peak Score: ${item['peakRiskIndex']}/100',
                  style: AppTextStyles.caption,
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Text(
                      'Outcome: ${item['outcome']}',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: isDanger
                            ? AppColors.danger
                            : AppColors.textSecondary,
                      ),
                    ),
                    const Spacer(),
                    Text(
                      'Verif: ${item['verificationStatus']}',
                      style: TextStyle(
                        fontSize: 11,
                        fontWeight: FontWeight.w600,
                        color: item['verificationStatus'] == 'Confirmed'
                            ? AppColors.success
                            : AppColors.warning,
                      ),
                    ),
                  ],
                ),
              ],
            ),
          ),
          trailing: const Icon(
            Icons.chevron_right_rounded,
            color: AppColors.textSecondary,
          ),
        ),
      ),
    );
  }
}
