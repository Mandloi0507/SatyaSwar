import 'package:flutter/material.dart';

import '../models/risk_band.dart';
import '../theme/app_colors.dart';
import '../theme/app_text_styles.dart';
import '../widgets/common/app_scaffold.dart';
import '../widgets/common/empty_state.dart';
import '../widgets/common/error_state.dart';
import '../widgets/common/glass_card.dart';
import '../widgets/common/primary_button.dart';
import '../widgets/common/risk_band_badge.dart';
import '../widgets/common/status_chip.dart';

class StyleGuideScreen extends StatelessWidget {
  const StyleGuideScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(title: const Text('Design System & Components')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const Text('SATYASWAR DESIGN SYSTEM', style: AppTextStyles.caption),
            const SizedBox(height: 4),
            const Text('Cybersecurity Foundation', style: AppTextStyles.title),
            const SizedBox(height: 20),

            // Typography Showcase
            const Text('Typography', style: AppTextStyles.sectionHeader),
            const SizedBox(height: 12),
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.border),
              ),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('91', style: AppTextStyles.displayRisk),
                  const Text('Title 22px SemiBold', style: AppTextStyles.title),
                  const SizedBox(height: 6),
                  const Text(
                    'Section Header 16px',
                    style: AppTextStyles.sectionHeader,
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Body regular 14px typography for instructions.',
                    style: AppTextStyles.body,
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'Caption 12px secondary metadata',
                    style: AppTextStyles.caption,
                  ),
                  const SizedBox(height: 6),
                  const Text(
                    'MATCH CODE: 47',
                    style: AppTextStyles.monospaceCode,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Risk Band Badges
            const Text(
              'Risk Band Badges (Section 6.2)',
              style: AppTextStyles.sectionHeader,
            ),
            const SizedBox(height: 12),
            const Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                RiskBandBadge(band: RiskBand.low),
                RiskBandBadge(band: RiskBand.medium),
                RiskBandBadge(band: RiskBand.high),
                RiskBandBadge(band: RiskBand.unknown),
              ],
            ),
            const SizedBox(height: 24),

            // Status Chips
            const Text('Status Chips', style: AppTextStyles.sectionHeader),
            const SizedBox(height: 12),
            const Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                StatusChip(label: 'Protection Ready', tone: StatusTone.success),
                StatusChip(label: 'Reconnecting', tone: StatusTone.warning),
                StatusChip(label: 'Server Offline', tone: StatusTone.danger),
                StatusChip(label: 'Mock Mode Active', tone: StatusTone.primary),
              ],
            ),
            const SizedBox(height: 24),

            // Buttons
            const Text('Action Buttons', style: AppTextStyles.sectionHeader),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'Primary Action',
              onPressed: () {},
              icon: Icons.shield_rounded,
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'Secondary Action',
              variant: ButtonVariant.secondary,
              onPressed: () {},
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'Destructive / End Call',
              variant: ButtonVariant.destructive,
              icon: Icons.call_end_rounded,
              onPressed: () {},
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'Loading Button',
              isLoading: true,
              onPressed: () {},
            ),
            const SizedBox(height: 24),

            // Glassmorphism Card
            const Text(
              'Selective Glassmorphism (Section 6.4)',
              style: AppTextStyles.sectionHeader,
            ),
            const SizedBox(height: 12),
            GlassCard(
              child: Row(
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: AppColors.primary.withValues(alpha: 0.2),
                      shape: BoxShape.circle,
                    ),
                    child: const Icon(
                      Icons.blur_on_rounded,
                      color: AppColors.primaryGlow,
                    ),
                  ),
                  const SizedBox(width: 14),
                  const Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Active Call Glass Overlay',
                          style: AppTextStyles.sectionHeader,
                        ),
                        SizedBox(height: 4),
                        Text(
                          '12px backdrop blur, 8% white fill, 1px subtle border.',
                          style: AppTextStyles.caption,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // Empty & Error states preview
            const Text(
              'Empty & Error States',
              style: AppTextStyles.sectionHeader,
            ),
            const SizedBox(height: 12),
            Container(
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppColors.border),
              ),
              child: const EmptyState(
                icon: Icons.group_off_rounded,
                title: 'No Trusted Contacts',
                description: 'Link with a family member or colleague to enable independent caller verification.',
                actionLabel: 'Add First Contact',
              ),
            ),
            const SizedBox(height: 16),
            Container(
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(18),
                border: Border.all(color: AppColors.border),
              ),
              child: const ErrorState(
                title: 'Analysis Unavailable',
                message: 'Failed to establish WebSocket stream with the analysis server.',
                technicalDetail:
                    'Connection refused: ws://192.168.43.10:8000/ws/call/102',
              ),
            ),
            const SizedBox(height: 40),
          ],
        ),
      ),
    );
  }
}
