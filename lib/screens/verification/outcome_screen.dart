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
    final isDanger = peakBand == RiskBand.high;

    return AppScaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 24.0, vertical: 32.0),
        child: Column(
          children: [
            const SizedBox(height: 16),
            // Result Icon Header
            Container(
              width: 90,
              height: 90,
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
                size: 50,
                color: isDanger ? AppColors.danger : AppColors.success,
              ),
            ),
            const SizedBox(height: 24),

            // Headline
            Text(
              isDanger
                  ? 'Likely Impersonation Detected'
                  : 'No Synthetic Indicators Detected',
              style: AppTextStyles.title.copyWith(fontSize: 24),
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 10),
            Text(
              isDanger
                  ? 'Do not transfer funds, share OTPs, or disclose confidential information on this call.'
                  : 'Acoustic parameters nominal. Low risk is not proof of identity—always verify independently before executing financial transactions.',
              style: AppTextStyles.bodySecondary,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 28),

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
                        'Peak Risk Assessment',
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
                        isDanger ? 'DENIED / MISMATCH' : 'CONFIRMED',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: isDanger
                              ? AppColors.danger
                              : AppColors.success,
                        ),
                      ),
                    ],
                  ),
                  const Divider(height: 24),
                  const Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      Text(
                        'Server Decision',
                        style: AppTextStyles.bodySecondary,
                      ),
                      Text(
                        'Block Sensitive Action',
                        style: TextStyle(
                          fontWeight: FontWeight.w700,
                          color: AppColors.danger,
                        ),
                      ),
                    ],
                  ),
                ],
              ),
            ),
            const SizedBox(height: 36),

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
