import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/primary_button.dart';

class ResponderScreen extends StatefulWidget {
  const ResponderScreen({super.key});

  @override
  State<ResponderScreen> createState() => _ResponderScreenState();
}

class _ResponderScreenState extends State<ResponderScreen> {
  String? _selectedMatchCode;
  bool _isBiometricVerified = false;

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(title: const Text('Responder Verification Gate')),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.border),
              ),
              child: const Row(
                children: [
                  Icon(
                    Icons.security_update_warning_rounded,
                    color: AppColors.warning,
                    size: 28,
                  ),
                  SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Incoming Verification Request',
                          style: AppTextStyles.sectionHeader,
                        ),
                        SizedBox(height: 4),
                        Text(
                          'Priyanka Mandloi is requesting caller verification for a ₹50,000 transfer.',
                          style: AppTextStyles.caption,
                        ),
                      ],
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 24),

            const Text(
              'Critical Security Question:',
              style: AppTextStyles.caption,
            ),
            const SizedBox(height: 4),
            const Text(
              'Are you on a phone call with Priyanka Mandloi right now?',
              style: AppTextStyles.subtitle,
            ),
            const SizedBox(height: 20),

            const Text(
              'Select the 2-digit match code you see on their screen:',
              style: AppTextStyles.bodySecondary,
            ),
            const SizedBox(height: 12),

            Row(
              children: ['47', '82', '19'].map((code) {
                final isSelected = _selectedMatchCode == code;
                return Expanded(
                  child: GestureDetector(
                    onTap: () => setState(() => _selectedMatchCode = code),
                    child: Container(
                      margin: const EdgeInsets.symmetric(horizontal: 4),
                      padding: const EdgeInsets.symmetric(vertical: 18),
                      decoration: BoxDecoration(
                        color: isSelected
                            ? AppColors.primary.withValues(alpha: 0.18)
                            : AppColors.surface,
                        borderRadius: BorderRadius.circular(14),
                        border: Border.all(
                          color: isSelected
                              ? AppColors.primaryGlow
                              : AppColors.border,
                          width: isSelected ? 2 : 1,
                        ),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        code,
                        style: TextStyle(
                          fontSize: 24,
                          fontWeight: FontWeight.w700,
                          fontFamily: 'monospace',
                          color: isSelected
                              ? AppColors.primaryGlow
                              : AppColors.textPrimary,
                        ),
                      ),
                    ),
                  ),
                );
              }).toList(),
            ),
            const SizedBox(height: 24),

            // Biometric simulation gate
            Container(
              padding: const EdgeInsets.all(16),
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(16),
                border: Border.all(color: AppColors.border),
              ),
              child: Row(
                children: [
                  Icon(
                    _isBiometricVerified
                        ? Icons.fingerprint_rounded
                        : Icons.lock_outline_rounded,
                    color: _isBiometricVerified
                        ? AppColors.success
                        : AppColors.textSecondary,
                    size: 28,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Biometric / Device PIN Gate',
                          style: AppTextStyles.sectionHeader,
                        ),
                        Text(
                          _isBiometricVerified
                              ? 'Identity Authenticated'
                              : 'Required before response submission',
                          style: AppTextStyles.caption,
                        ),
                      ],
                    ),
                  ),
                  TextButton(
                    onPressed: () =>
                        setState(() => _isBiometricVerified = true),
                    child: Text(
                      _isBiometricVerified ? 'Verified' : 'Authenticate',
                    ),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 32),

            PrimaryButton(
              label: 'YES, I am on the call (Confirm)',
              icon: Icons.check_circle_rounded,
              onPressed: _selectedMatchCode != null && _isBiometricVerified
                  ? () {
                      ScaffoldMessenger.of(context).showSnackBar(
                        const SnackBar(
                          content: Text('Caller verification confirmed'),
                        ),
                      );
                      Navigator.pop(context);
                    }
                  : null,
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'NO, I am NOT on the call (Deny Fraud)',
              variant: ButtonVariant.destructive,
              icon: Icons.dangerous_rounded,
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Impersonation alert sent to requester!'),
                  ),
                );
                Navigator.pop(context);
              },
            ),
          ],
        ),
      ),
    );
  }
}
