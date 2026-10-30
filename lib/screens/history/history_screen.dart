import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:provider/provider.dart';

import '../../models/call_history_record.dart';
import '../../models/risk_band.dart';
import '../../providers/call_history_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/empty_state.dart';
import '../../widgets/common/risk_band_badge.dart';

class HistoryScreen extends StatelessWidget {
  const HistoryScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final historyProvider = context.watch<CallHistoryProvider>();
    final records = historyProvider.records;

    return AppScaffold(
      appBar: AppBar(title: const Text('Call History (Scores-Only)')),
      body: RefreshIndicator(
        onRefresh: () => historyProvider.loadHistory(),
        color: AppColors.primaryGlow,
        backgroundColor: AppColors.surfaceHigh,
        child: ListView(
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

            if (historyProvider.isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (records.isEmpty)
              const EmptyState(
                icon: Icons.history_rounded,
                title: 'No Call History',
                description:
                    'Simulated call logs will appear here after calls complete.',
              )
            else
              ...records.map((r) => _buildHistoryCard(context, r)),
          ],
        ),
      ),
    );
  }

  Widget _buildHistoryCard(BuildContext context, CallHistoryRecord item) {
    final isDanger = item.peakRiskBand == RiskBand.high;
    final formattedDate =
        DateFormat('MMM d, hh:mm a').format(item.timestamp);

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
          contentPadding:
              const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
          onTap: () => context.push('/history/${item.id}'),
          leading: CircleAvatar(
            backgroundColor: isDanger
                ? AppColors.danger.withValues(alpha: 0.15)
                : AppColors.surfaceHigh,
            child: Icon(
              isDanger
                  ? Icons.warning_amber_rounded
                  : Icons.phone_callback_rounded,
              color: isDanger ? AppColors.danger : AppColors.primaryGlow,
            ),
          ),
          title: Text(
            item.callerName,
            style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
          ),
          subtitle: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SizedBox(height: 4),
              Text(
                '$formattedDate • ${item.durationSeconds}s',
                style: AppTextStyles.caption,
              ),
              const SizedBox(height: 2),
              Text(
                'Status: ${item.verificationStatus.toUpperCase()} • ${item.finalOutcome}',
                style: TextStyle(
                  fontSize: 11,
                  color: isDanger ? AppColors.danger : AppColors.textSecondary,
                  fontWeight: isDanger ? FontWeight.w600 : FontWeight.normal,
                ),
              ),
            ],
          ),
          trailing: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.end,
            children: [
              RiskBandBadge(band: item.peakRiskBand, compact: true),
              const SizedBox(height: 4),
              Text(
                'Peak: ${item.peakRiskScore}',
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textSecondary,
                  fontFamily: 'monospace',
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
