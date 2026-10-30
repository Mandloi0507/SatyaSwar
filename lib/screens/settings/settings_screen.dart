import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../config/app_config.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/primary_button.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _serverUrlController = TextEditingController(
    text: AppConfig.defaultServerUrl,
  );
  bool _useMocks = true;
  double _alertVolume = 0.85;

  @override
  void dispose() {
    _serverUrlController.dispose();
    super.dispose();
  }

  void _testConnection() {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text('Testing connection to ${_serverUrlController.text}...'),
        duration: const Duration(seconds: 2),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(title: const Text('Application Settings')),
      body: ListView(
        padding: const EdgeInsets.all(20.0),
        children: [
          // Section 1: Server & Connectivity
          const Text(
            'ANALYSIS SERVER INTEGRATION',
            style: AppTextStyles.caption,
          ),
          const SizedBox(height: 10),
          Container(
            padding: const EdgeInsets.all(16),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                const Text(
                  'Backend Host Endpoint',
                  style: AppTextStyles.sectionHeader,
                ),
                const SizedBox(height: 8),
                TextFormField(
                  controller: _serverUrlController,
                  style: const TextStyle(
                    color: AppColors.textPrimary,
                    fontFamily: 'monospace',
                    fontSize: 13,
                  ),
                  decoration: const InputDecoration(
                    prefixIcon: Icon(
                      Icons.dns_rounded,
                      color: AppColors.textSecondary,
                    ),
                  ),
                ),
                const SizedBox(height: 14),
                PrimaryButton(
                  label: 'Test Connection',
                  variant: ButtonVariant.secondary,
                  icon: Icons.network_check_rounded,
                  height: 44,
                  onPressed: _testConnection,
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Section 2: Demo Mode Toggles
          const Text(
            'PROTOTYPE & DEMONSTRATION CONTROLS',
            style: AppTextStyles.caption,
          ),
          const SizedBox(height: 10),
          Container(
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              children: [
                SwitchListTile(
                  title: const Text(
                    'Mock Services Mode',
                    style: AppTextStyles.sectionHeader,
                  ),
                  subtitle: const Text(
                    'Simulates server risk scores locally when laptop backend is unreachable.',
                    style: AppTextStyles.caption,
                  ),
                  value: _useMocks,
                  activeThumbColor: AppColors.primaryGlow,
                  onChanged: (val) => setState(() => _useMocks = val),
                ),
                const Divider(),
                ListTile(
                  title: const Text(
                    'Spoken Alert Volume',
                    style: AppTextStyles.sectionHeader,
                  ),
                  subtitle: Slider(
                    value: _alertVolume,
                    min: 0.0,
                    max: 1.0,
                    activeColor: AppColors.primaryGlow,
                    inactiveColor: AppColors.surfaceHigh,
                    onChanged: (val) => setState(() => _alertVolume = val),
                  ),
                  trailing: Text(
                    '${(_alertVolume * 100).round()}%',
                    style: const TextStyle(
                      fontWeight: FontWeight.w600,
                      color: AppColors.textPrimary,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // Section 3: User Account & Verification Gate
          const Text('ACCOUNT & PROTOCOL', style: AppTextStyles.caption),
          const SizedBox(height: 10),
          Container(
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(18),
              border: Border.all(color: AppColors.border),
            ),
            child: Column(
              children: [
                ListTile(
                  leading: const Icon(
                    Icons.person_pin_rounded,
                    color: AppColors.primaryGlow,
                  ),
                  title: const Text(
                    'Simulate Second Phone Responder',
                    style: AppTextStyles.body,
                  ),
                  subtitle: const Text(
                    'Open verification challenge responder gate',
                    style: AppTextStyles.caption,
                  ),
                  trailing: const Icon(
                    Icons.chevron_right_rounded,
                    color: AppColors.textSecondary,
                  ),
                  onTap: () => context.push('/responder'),
                ),
                const Divider(),
                ListTile(
                  leading: const Icon(
                    Icons.palette_outlined,
                    color: AppColors.primaryGlow,
                  ),
                  title: const Text(
                    'Component Style Guide',
                    style: AppTextStyles.body,
                  ),
                  subtitle: const Text(
                    'Inspect all UI widgets in every state',
                    style: AppTextStyles.caption,
                  ),
                  trailing: const Icon(
                    Icons.chevron_right_rounded,
                    color: AppColors.textSecondary,
                  ),
                  onTap: () => context.push('/style-guide'),
                ),
                const Divider(),
                ListTile(
                  leading: const Icon(
                    Icons.logout_rounded,
                    color: AppColors.danger,
                  ),
                  title: const Text(
                    'Sign Out',
                    style: TextStyle(
                      color: AppColors.danger,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  onTap: () => context.go('/login'),
                ),
              ],
            ),
          ),
          const SizedBox(height: 24),

          // App Info
          const Center(
            child: Text(
              '${AppConfig.appName} v${AppConfig.appVersion} • SIH 2026 PS 26104',
              style: TextStyle(color: AppColors.textMuted, fontSize: 11),
            ),
          ),
          const SizedBox(height: 20),
        ],
      ),
    );
  }
}
