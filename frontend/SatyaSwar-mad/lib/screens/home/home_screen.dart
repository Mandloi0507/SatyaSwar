import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../models/risk_band.dart';
import '../../providers/auth_provider.dart';
import '../../providers/call_history_provider.dart';
import '../../providers/contacts_provider.dart';
import '../../providers/settings_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/glass_card.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/risk_band_badge.dart';
import '../../widgets/common/status_chip.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final auth = context.watch<AuthProvider>();
    final settings = context.watch<SettingsProvider>();
    final contacts = context.watch<ContactsProvider>();
    final history = context.watch<CallHistoryProvider>();

    final userName = auth.currentUser?.displayName ?? 'User';
    final contactCount = contacts.contacts.length;
    final recentCalls = history.records.take(3).toList();

    return AppScaffold(
      body: SingleChildScrollView(
        padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // 1. Top Bar / Greeting & Security Status Chip
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      'Welcome back',
                      style: AppTextStyles.caption.copyWith(
                        color: AppColors.textSecondary,
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(userName, style: AppTextStyles.title),
                  ],
                ),
                Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    if (settings.isMockMode)
                      Container(
                        margin: const EdgeInsets.only(right: 8),
                        padding: const EdgeInsets.symmetric(
                          horizontal: 8,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.warning.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(
                            color: AppColors.warning.withValues(alpha: 0.4),
                          ),
                        ),
                        child: const Text(
                          'MOCK',
                          style: TextStyle(
                            color: AppColors.warning,
                            fontSize: 10,
                            fontWeight: FontWeight.w700,
                            letterSpacing: 0.8,
                          ),
                        ),
                      ),
                    const StatusChip(
                      label: 'Protection Ready',
                      tone: StatusTone.success,
                    ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 24),

            // 2. Large Primary Card "Start Simulated Call"
            Container(
              decoration: BoxDecoration(
                borderRadius: BorderRadius.circular(22),
                gradient: const LinearGradient(
                  colors: [AppColors.surfaceHigh, AppColors.surface],
                  begin: Alignment.topLeft,
                  end: Alignment.bottomRight,
                ),
                border: Border.all(
                  color: AppColors.primary.withValues(alpha: 0.35),
                  width: 1.5,
                ),
                boxShadow: [
                  BoxShadow(
                    color: AppColors.primary.withValues(alpha: 0.12),
                    blurRadius: 24,
                    offset: const Offset(0, 8),
                  ),
                ],
              ),
              padding: const EdgeInsets.all(20),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(12),
                        decoration: BoxDecoration(
                          color: AppColors.primary.withValues(alpha: 0.18),
                          borderRadius: BorderRadius.circular(14),
                        ),
                        child: const Icon(
                          Icons.phone_in_talk_rounded,
                          color: AppColors.primaryGlow,
                          size: 28,
                        ),
                      ),
                      const SizedBox(width: 14),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Voice Integrity Shield',
                              style: AppTextStyles.subtitle,
                            ),
                            SizedBox(height: 4),
                            Text(
                              'Simulate an incoming suspicious or genuine call scenario to test real-time AI detection.',
                              style: AppTextStyles.caption,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  PrimaryButton(
                    label: 'Start Simulated Call',
                    icon: Icons.play_arrow_rounded,
                    onPressed: () => context.push('/call/scenarios'),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            // 3. Row of Shortcuts (Trusted Contacts, Style Guide / Test)
            Row(
              children: [
                Expanded(
                  child: GlassCard(
                    padding: const EdgeInsets.all(14),
                    onTap: () => context.go('/contacts'),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Icon(
                          Icons.shield_outlined,
                          color: AppColors.primaryGlow,
                          size: 24,
                        ),
                        const SizedBox(height: 10),
                        const Text(
                          'Trusted Contacts',
                          style: AppTextStyles.sectionHeader,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          '$contactCount Registered',
                          style: AppTextStyles.caption,
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(width: 14),
                Expanded(
                  child: GlassCard(
                    padding: const EdgeInsets.all(14),
                    onTap: () => context.go('/history'),
                    child: const Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(
                          Icons.timeline_rounded,
                          color: AppColors.riskLow,
                          size: 24,
                        ),
                        SizedBox(height: 10),
                        Text('History Log', style: AppTextStyles.sectionHeader),
                        SizedBox(height: 2),
                        Text('Scores Only', style: AppTextStyles.caption),
                      ],
                    ),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 24),

            // 4. Recent Calls Header
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                const Text('Recent Calls', style: AppTextStyles.subtitle),
                TextButton(
                  onPressed: () => context.go('/history'),
                  child: const Text('View All'),
                ),
              ],
            ),
            const SizedBox(height: 12),

            if (recentCalls.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 16.0),
                child: Center(
                  child: Text(
                    'No recent simulated calls yet.',
                    style: AppTextStyles.bodySecondary,
                  ),
                ),
              )
            else
              ...recentCalls.map(
                (call) => Padding(
                  padding: const EdgeInsets.only(bottom: 10.0),
                  child: _buildRecentCallTile(
                    caller: call.callerName,
                    timeAgo: _formatTimeAgo(call.timestamp),
                    band: call.peakRiskBand,
                    riskIndex: call.peakRiskScore,
                    verification: call.verificationStatus == 'confirmed'
                        ? 'Confirmed'
                        : (call.verificationStatus == 'denied'
                            ? 'Denied'
                            : 'Unverified'),
                    onTap: () => context.push('/history/${call.id}'),
                  ),
                ),
              ),

            const SizedBox(height: 24),

            // 5. Mandatory Prototype Disclaimer Footer (GEMINI.md Rule 2)
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 10),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(12),
                border: Border.all(color: AppColors.border),
              ),
              child: const Row(
                children: [
                  Icon(
                    Icons.info_outline_rounded,
                    size: 16,
                    color: AppColors.textSecondary,
                  ),
                  SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      'Calls in this prototype are simulated inside the application. No cellular network audio is captured.',
                      style: TextStyle(
                        color: AppColors.textSecondary,
                        fontSize: 11,
                      ),
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 20),
          ],
        ),
      ),
    );
  }

  String _formatTimeAgo(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inMinutes < 60) {
      return '${diff.inMinutes} min ago';
    } else if (diff.inHours < 24) {
      return '${diff.inHours} hours ago';
    } else {
      return '${diff.inDays} days ago';
    }
  }

  Widget _buildRecentCallTile({
    required String caller,
    required String timeAgo,
    required RiskBand band,
    required int riskIndex,
    required String verification,
    required VoidCallback onTap,
  }) {
    return Material(
      color: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(16),
        side: const BorderSide(color: AppColors.border),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
        onTap: onTap,
        leading: CircleAvatar(
          backgroundColor: AppColors.surfaceHigh,
          child: Text(
            caller.isNotEmpty ? caller[0] : '?',
            style: const TextStyle(
              color: AppColors.primaryGlow,
              fontWeight: FontWeight.w600,
            ),
          ),
        ),
        title: Text(
          caller,
          style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          '$timeAgo • $verification',
          style: AppTextStyles.caption,
        ),
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            RiskBandBadge(band: band, compact: true),
            const SizedBox(width: 8),
            const Icon(
              Icons.chevron_right_rounded,
              color: AppColors.textSecondary,
              size: 20,
            ),
          ],
        ),
      ),
    );
  }
}
