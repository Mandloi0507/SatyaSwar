import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../models/risk_band.dart';
import '../../providers/call_history_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/risk_band_badge.dart';
import '../../widgets/risk/score_timeline_chart.dart';

class HistoryDetailScreen extends StatelessWidget {
  final String callId;
  final Map<String, dynamic>? itemData;

  const HistoryDetailScreen({super.key, required this.callId, this.itemData});

  @override
  Widget build(BuildContext context) {
    final history = context.watch<CallHistoryProvider>();
    final record = history.records.where((r) => r.id == callId).firstOrNull;

    final contact = record?.callerName ??
        (itemData?['claimedContact'] as String? ?? 'Rakesh Sir (CEO)');
    final date = record != null
        ? DateFormat('MMM d, yyyy • hh:mm a').format(record.timestamp)
        : (itemData?['date'] as String? ?? 'Today, 03:15 PM');
    final peakIndex = record?.peakRiskScore ??
        (itemData?['peakRiskIndex'] as int? ?? 91);
    final band = record?.peakRiskBand ??
        (itemData?['peakBand'] as RiskBand? ?? RiskBand.high);
    final verif = record?.verificationStatus ??
        (itemData?['verificationStatus'] as String? ?? 'Denied');
    final outcome = record?.finalOutcome ??
        (itemData?['outcome'] as String? ?? 'Likely Impersonation');
    final timeline = record?.timelineScores ??
        const [14, 22, 54, 76, 88, 91];

    final isConfirmed = verif.toLowerCase() == 'confirmed';

    return AppScaffold(
      appBar: AppBar(title: const Text('Call Record Detail')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(20),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(20),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Claimed Caller',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Text(contact, style: AppTextStyles.subtitle),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Call Timestamp',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Text(date, style: AppTextStyles.body),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Peak Risk Index',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Row(
                        children: [
                          Text(
                            '$peakIndex / 100  ',
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          RiskBandBadge(band: band, compact: true),
                        ],
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Independent Verification',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Text(
                        verif.toUpperCase(),
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: isConfirmed
                              ? AppColors.success
                              : AppColors.danger,
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Final Security Outcome',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Text(
                        outcome,
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: band == RiskBand.high
                              ? AppColors.danger
                              : AppColors.success,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            const Text(
              'Acoustic Timeline Progression',
              style: AppTextStyles.sectionHeader,
            ),
            const SizedBox(height: 12),
            ScoreTimelineChart(windowScores: timeline),
            const SizedBox(height: 24),

            Container(
              padding: const EdgeInsets.all(14),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(14),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  const Icon(
                    Icons.verified_outlined,
                    size: 20,
                    color: AppColors.primaryGlow,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Text(
                      'Session callId: $callId\nThis audit trail record is preserved for fraud reporting. No acoustic media or transcripts are stored.',
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                        height: 1.4,
                      ),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
