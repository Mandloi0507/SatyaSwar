import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../models/risk_band.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/risk_band_badge.dart';

class OutcomeScreen extends StatelessWidget {
  final Map<String, dynamic>? outcomeData;

  const OutcomeScreen({super.key, this.outcomeData});

  @override
  Widget build(BuildContext context) {
    final claimedName = outcomeData?['claimedName'] as String? ?? 'Rakesh Sir';
    final peakRiskIndex = outcomeData?['peakRiskIndex'] as int? ?? 88;
    final peakBand = outcomeData?['peakBand'] as RiskBand? ?? RiskBand.high;
    final isMock = outcomeData?['isMock'] as bool? ?? true;
    final serverOutcome = outcomeData?['serverReportedOutcome'] as String? ??
        (isMock
            ? 'Simulated session completed (Offline Mock)'
            : 'Analysis session ended');
    final verificationStatus =
        outcomeData?['verificationStatus'] as String? ?? 'Unverified';
    final isDanger = peakBand == RiskBand.high;

    return AppScaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 28.0),
        child: Column(
          children: [
            // 1. Prominent Mock / Simulation Label
            if (isMock)
              Container(
                margin: const EdgeInsets.only(bottom: 20),
                padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
                decoration: BoxDecoration(
                  color: AppColors.warning.withValues(alpha: 0.15),
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(
                    color: AppColors.warning.withValues(alpha: 0.5),
                  ),
                ),
                child: const Row(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(
                      Icons.science_outlined,
                      size: 16,
                      color: AppColors.warning,
                    ),
                    SizedBox(width: 8),
                    Flexible(
                      child: Text(
                        'SIMULATED CALL OUTCOME • Offline Mock Data • Not Real ML Inference',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.warning,
                          letterSpacing: 0.3,
                        ),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ],
                ),
              ),

            // Result Icon Header
            Container(
              width: 84,
              height: 84,
              decoration: BoxDecoration(
                shape: BoxShape.circle,
                color: isDanger
                    ? AppColors.danger.withValues(alpha: 0.18)
                    : AppColors.success.withValues(alpha: 0.18),
                border: Border.all(
                  color: isDanger ? AppColors.danger : AppColors.success,
                  width: 2,
                ),
              ),
              child: Icon(
                isDanger ? Icons.gpp_bad_rounded : Icons.verified_user_rounded,
                size: 46,
                color: isDanger ? AppColors.danger : AppColors.success,
              ),
            ),
            const SizedBox(height: 20),

            // Headline (Reflecting acoustic risk indicators, not definitive client verdict)
            Text(
              isDanger
                  ? 'High Risk Acoustic Indicators'
                  : 'Nominal Acoustic Parameters',
              style: AppTextStyles.title.copyWith(fontSize: 22),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              isDanger
                  ? 'Voice analysis observed synthetic speech characteristics. Exercise caution and verify caller before sharing sensitive details or executing transactions.'
                  : 'No significant synthetic characteristics observed during this sample. Low acoustic risk is not proof of identity—always verify independently for sensitive requests.',
              style: AppTextStyles.bodySecondary,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 24),

            // Analysis Summary Card
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
                        'Claimed Identity',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Text(
                        claimedName,
                        style: AppTextStyles.body.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Peak Risk Metric',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Row(
                        children: [
                          Text(
                            '$peakRiskIndex / 100  ',
                            style: const TextStyle(
                              fontWeight: FontWeight.w700,
                              color: AppColors.textPrimary,
                            ),
                          ),
                          RiskBandBadge(band: peakBand, compact: true),
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
                        verificationStatus.toUpperCase(),
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: verificationStatus.toLowerCase() == 'verified'
                              ? AppColors.success
                              : AppColors.warning,
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Text(
                        'Reported Status',
                        style: AppTextStyles.bodySecondary,
                      ),
                      const SizedBox(width: 16),
                      Expanded(
                        child: Text(
                          serverOutcome,
                          style: const TextStyle(
                            fontWeight: FontWeight.w600,
                            color: AppColors.textPrimary,
                            fontSize: 13,
                          ),
                          textAlign: TextAlign.end,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 16),

            // Transparency Disclaimer
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: const Text(
                'Security Notice: The mobile app visualizes incoming risk scores and never calculates definitive authenticity decisions locally. All final decisions require backend model inference and trusted out-of-band contact confirmation.',
                style: TextStyle(
                  color: AppColors.textSecondary,
                  fontSize: 11,
                  height: 1.4,
                ),
                textAlign: TextAlign.center,
              ),
            ),
            const SizedBox(height: 28),

            // Action Buttons
            PrimaryButton(
              label: 'Return to Protection Dashboard',
              icon: Icons.home_rounded,
              onPressed: () => context.go('/home'),
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'View in History Records',
              variant: ButtonVariant.secondary,
              icon: Icons.history_rounded,
              onPressed: () => context.go('/history'),
            ),
          ],
        ),
      ),
    );
  }
}
