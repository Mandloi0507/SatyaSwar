import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import '../../providers/verification_provider.dart';
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
  bool _isAuthenticating = false;

  void _handleBiometricAuth() async {
    setState(() => _isAuthenticating = true);
    final verif = context.read<VerificationProvider>();
    final success = await verif.authenticateBiometric();
    if (!mounted) return;
    setState(() {
      _isBiometricVerified = success;
      _isAuthenticating = false;
    });

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Identity verified via biometric/PIN convenience gate'),
          backgroundColor: AppColors.success,
        ),
      );
    }
  }

  void _handleApprove() async {
    final verif = context.read<VerificationProvider>();
    final currentReq = verif.currentRequest;
    if (currentReq != null) {
      await verif.responderApprove(currentReq.requestId);
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Caller verification CONFIRMED as trusted contact.'),
        backgroundColor: AppColors.success,
      ),
    );
    Navigator.pop(context);
  }

  void _handleDeny() async {
    final verif = context.read<VerificationProvider>();
    final currentReq = verif.currentRequest;
    if (currentReq != null) {
      await verif.responderDeny(currentReq.requestId);
    }
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('Fraud alert triggered: Impersonation reported!'),
        backgroundColor: AppColors.danger,
      ),
    );
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final verif = context.watch<VerificationProvider>();
    final req = verif.currentRequest;

    final targetName = req?.claimedIdentity ?? 'Rakesh Sir';
    final actionDesc = req?.action ?? '₹50,000 transfer';
    final activeCode = req?.matchCode ?? 'SW79';

    // Options for match code selection
    final codeOptions = [activeCode, '47', '82'];

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
              child: Row(
                children: [
                  const Icon(
                    Icons.security_update_warning_rounded,
                    color: AppColors.warning,
                    size: 28,
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        const Text(
                          'Incoming Verification Challenge',
                          style: AppTextStyles.sectionHeader,
                        ),
                        const SizedBox(height: 4),
                        Text(
                          'A user is requesting caller verification for claimed caller "$targetName" ($actionDesc).',
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
            Text(
              'Are you on a phone call with this person right now?',
              style: AppTextStyles.subtitle,
            ),
            const SizedBox(height: 20),

            const Text(
              'Select the match code displayed on the caller\'s phone:',
              style: AppTextStyles.bodySecondary,
            ),
            const SizedBox(height: 12),

            Row(
              children: codeOptions.map((code) {
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
                          fontSize: 22,
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

            // Biometric gate
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
                    onPressed: _isAuthenticating ? null : _handleBiometricAuth,
                    child: Text(
                      _isBiometricVerified
                          ? 'Verified'
                          : (_isAuthenticating ? 'Checking...' : 'Authenticate'),
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
                  ? _handleApprove
                  : null,
            ),
            const SizedBox(height: 12),
            PrimaryButton(
              label: 'NO, I am NOT on the call (Deny Fraud)',
              variant: ButtonVariant.destructive,
              icon: Icons.dangerous_rounded,
              onPressed: _handleDeny,
            ),
          ],
        ),
      ),
    );
  }
}
