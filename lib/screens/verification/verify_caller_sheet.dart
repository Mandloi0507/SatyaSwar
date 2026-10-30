import 'dart:async';

import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/glass_card.dart';
import '../../widgets/common/primary_button.dart';

class VerifyCallerSheet extends StatefulWidget {
  final String claimedName;

  const VerifyCallerSheet({super.key, required this.claimedName});

  @override
  State<VerifyCallerSheet> createState() => _VerifyCallerSheetState();
}

class _VerifyCallerSheetState extends State<VerifyCallerSheet> {
  int _currentStep =
      1; // 1: Choose Contact, 2: Action Type, 3: Pending Challenge

  String? _selectedContact;
  String _selectedAction = 'money_transfer';
  final _amountController = TextEditingController();

  // Challenge Code & Countdown for Step 3
  final String _matchCode = '47';
  int _secondsRemaining = 60;
  Timer? _countdownTimer;
  String _verificationStatus = 'Pending responder confirmation...';

  @override
  void dispose() {
    _countdownTimer?.cancel();
    _amountController.dispose();
    super.dispose();
  }

  void _startPendingVerification() {
    setState(() => _currentStep = 3);
    _countdownTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      if (_secondsRemaining > 1) {
        setState(() => _secondsRemaining--);
        if (_secondsRemaining == 52) {
          // Simulate responder denial in synthetic test
          setState(() {
            _verificationStatus = 'VERIFICATION DENIED: Contact confirmed they are NOT on a call with you!';
          });
        }
      } else {
        _countdownTimer?.cancel();
        setState(() {
          _verificationStatus =
              'VERIFICATION EXPIRED: No response received within 60 seconds.';
        });
      }
    });
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: const BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
        border: Border(top: BorderSide(color: AppColors.border, width: 1.5)),
      ),
      padding: EdgeInsets.only(
        top: 16,
        left: 20,
        right: 20,
        bottom: MediaQuery.of(context).viewInsets.bottom + 24,
      ),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          // Drag handle
          Container(
            width: 40,
            height: 4,
            decoration: BoxDecoration(
              color: AppColors.border,
              borderRadius: BorderRadius.circular(2),
            ),
          ),
          const SizedBox(height: 16),

          // Header
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(
                _currentStep == 1
                    ? 'Step 1: Select Claimed Contact'
                    : (_currentStep == 2
                          ? 'Step 2: Requested Action'
                          : 'Step 3: Independent Verification'),
                style: AppTextStyles.sectionHeader,
              ),
              IconButton(
                icon: const Icon(
                  Icons.close_rounded,
                  size: 20,
                  color: AppColors.textSecondary,
                ),
                onPressed: () => Navigator.pop(context),
              ),
            ],
          ),
          const Divider(),
          const SizedBox(height: 12),

          if (_currentStep == 1) _buildStep1SelectContact(),
          if (_currentStep == 2) _buildStep2SelectAction(),
          if (_currentStep == 3) _buildStep3PendingChallenge(),
        ],
      ),
    );
  }

  Widget _buildStep1SelectContact() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Who does the caller claim to be? Suggested based on scenario: "${widget.claimedName}".',
          style: AppTextStyles.bodySecondary,
        ),
        const SizedBox(height: 16),

        _buildContactRadioTile('Rakesh Verma (Rakesh Sir)', 'U204'),
        _buildContactRadioTile('Priyanka Sharma (Priti)', 'U102'),
        _buildContactRadioTile('Sunil Mehta (Sunil)', 'U309'),
        _buildContactRadioTile(
          'Not in my trusted contacts list',
          null,
          isUnmatched: true,
        ),

        const SizedBox(height: 20),
        PrimaryButton(
          label: 'Continue to Action',
          onPressed: _selectedContact != null
              ? () {
                  if (_selectedContact == 'not_matched') {
                    // Refusal to proceed
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'SatyaSwar cannot verify this caller. Do not proceed with this call.',
                        ),
                      ),
                    );
                  } else {
                    setState(() => _currentStep = 2);
                  }
                }
              : null,
        ),
      ],
    );
  }

  Widget _buildContactRadioTile(
    String name,
    String? code, {
    bool isUnmatched = false,
  }) {
    final valueKey = isUnmatched ? 'not_matched' : name;
    final isSelected = _selectedContact == valueKey;

    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: isSelected
            ? AppColors.primary.withValues(alpha: 0.12)
            : AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isSelected ? AppColors.primary : AppColors.border,
          width: isSelected ? 1.5 : 1.0,
        ),
      ),
      child: ListTile(
        leading: Icon(
          isSelected
              ? Icons.radio_button_checked_rounded
              : Icons.radio_button_off_rounded,
          color: isSelected ? AppColors.primaryGlow : AppColors.textSecondary,
        ),
        title: Text(
          name,
          style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
        ),
        subtitle: code != null
            ? Text('Trusted ID: $code', style: AppTextStyles.caption)
            : null,
        onTap: () => setState(() => _selectedContact = valueKey),
      ),
    );
  }

  Widget _buildStep2SelectAction() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'What is the caller requesting you to do on this call?',
          style: AppTextStyles.bodySecondary,
        ),
        const SizedBox(height: 14),

        _buildActionOption(
          'money_transfer',
          'Money Transfer / UPI Request',
          Icons.payment_rounded,
        ),
        _buildActionOption(
          'otp_credentials',
          'OTP / Banking Credentials',
          Icons.password_rounded,
        ),
        _buildActionOption(
          'confidential_info',
          'Confidential Corporate Info',
          Icons.lock_person_rounded,
        ),
        _buildActionOption(
          'other',
          'Other Request',
          Icons.help_outline_rounded,
        ),

        if (_selectedAction == 'money_transfer') ...[
          const SizedBox(height: 14),
          TextFormField(
            controller: _amountController,
            keyboardType: TextInputType.number,
            style: const TextStyle(color: AppColors.textPrimary),
            decoration: const InputDecoration(
              labelText: 'Transfer Amount (INR)',
              hintText: '50000',
              prefixText: '₹ ',
            ),
          ),
        ],

        const SizedBox(height: 20),
        PrimaryButton(
          label: 'Send Verification Challenge',
          icon: Icons.send_rounded,
          onPressed: _startPendingVerification,
        ),
      ],
    );
  }

  Widget _buildActionOption(String key, String title, IconData icon) {
    final isSelected = _selectedAction == key;
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      decoration: BoxDecoration(
        color: isSelected
            ? AppColors.primary.withValues(alpha: 0.12)
            : AppColors.surfaceHigh,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: isSelected ? AppColors.primary : AppColors.border,
          width: isSelected ? 1.5 : 1.0,
        ),
      ),
      child: ListTile(
        leading: Icon(
          icon,
          color: isSelected ? AppColors.primaryGlow : AppColors.textSecondary,
        ),
        title: Text(
          title,
          style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w500),
        ),
        trailing: isSelected
            ? const Icon(
                Icons.check_circle_rounded,
                color: AppColors.primaryGlow,
              )
            : null,
        onTap: () => setState(() => _selectedAction = key),
      ),
    );
  }

  Widget _buildStep3PendingChallenge() {
    final isDenied = _verificationStatus.contains('DENIED');

    return Column(
      children: [
        const Text(
          'A secure push challenge has been sent to the claimed contact\'s registered device. Ask them to confirm this match code:',
          style: AppTextStyles.bodySecondary,
          textAlign: TextAlign.center,
        ),
        const SizedBox(height: 18),

        // Match Code Display Box
        GlassCard(
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          child: Column(
            children: [
              const Text(
                'VERIFICATION MATCH CODE',
                style: AppTextStyles.caption,
              ),
              const SizedBox(height: 6),
              Text(
                _matchCode,
                style: const TextStyle(
                  fontSize: 52,
                  fontWeight: FontWeight.w700,
                  fontFamily: 'monospace',
                  letterSpacing: 4,
                  color: AppColors.primaryGlow,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                '$_secondsRemaining s remaining',
                style: TextStyle(
                  color: _secondsRemaining < 15
                      ? AppColors.danger
                      : AppColors.warning,
                  fontWeight: FontWeight.w600,
                  fontSize: 13,
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Status line
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: isDenied
                ? AppColors.danger.withValues(alpha: 0.18)
                : AppColors.surfaceHigh,
            borderRadius: BorderRadius.circular(12),
            border: Border.all(
              color: isDenied ? AppColors.danger : AppColors.border,
            ),
          ),
          child: Row(
            children: [
              Icon(
                isDenied ? Icons.dangerous_rounded : Icons.sync_rounded,
                color: isDenied ? AppColors.danger : AppColors.primaryGlow,
              ),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  _verificationStatus,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isDenied ? FontWeight.w700 : FontWeight.w500,
                    color: isDenied ? AppColors.danger : AppColors.textPrimary,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 20),

        PrimaryButton(
          label: isDenied ? 'Close & Take Action' : 'Cancel Verification',
          variant: isDenied
              ? ButtonVariant.destructive
              : ButtonVariant.secondary,
          onPressed: () => Navigator.pop(context),
        ),
      ],
    );
  }
}
