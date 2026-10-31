import 'package:flutter/material.dart';
import 'package:provider/provider.dart';
import '../../providers/contacts_provider.dart';
import '../../providers/verification_provider.dart';
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
  int _currentStep = 1; // 1: Select Contact, 2: Action Type, 3: Pending Challenge

  String? _selectedContactId;
  String? _selectedContactName;
  String _selectedAction = 'money_transfer';
  final _amountController = TextEditingController();

  @override
  void dispose() {
    _amountController.dispose();
    super.dispose();
  }

  void _startVerification() async {
    setState(() => _currentStep = 3);

    final verif = context.read<VerificationProvider>();
    final amount = double.tryParse(_amountController.text.trim());

    await verif.startVerification(
      callId: 'call_${DateTime.now().millisecondsSinceEpoch}',
      contactId: _selectedContactId ?? 'unknown',
      contactName: _selectedContactName ?? widget.claimedName,
      claimedIdentity: widget.claimedName,
      action: _selectedAction,
      amount: amount,
    );
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
                onPressed: () {
                  context.read<VerificationProvider>().cancelCurrent();
                  Navigator.pop(context);
                },
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
    final contactsProvider = context.watch<ContactsProvider>();
    final contacts = contactsProvider.contacts;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Who does the caller claim to be? Suggested based on scenario: "${widget.claimedName}".',
          style: AppTextStyles.bodySecondary,
        ),
        const SizedBox(height: 16),

        ...contacts.map(
          (c) => _buildContactRadioTile(
            id: c.id,
            name: c.name,
            alias: c.alias,
          ),
        ),

        _buildContactRadioTile(
          id: 'not_matched',
          name: 'Not in my trusted contacts list',
          alias: 'Unmatched',
          isUnmatched: true,
        ),

        const SizedBox(height: 20),
        PrimaryButton(
          label: 'Continue to Action',
          onPressed: _selectedContactId != null
              ? () {
                  if (_selectedContactId == 'not_matched') {
                    Navigator.pop(context);
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(
                        content: Text(
                          'Security Warning: Caller is not in your trusted network. Do not execute sensitive transactions.',
                        ),
                        backgroundColor: AppColors.danger,
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

  Widget _buildContactRadioTile({
    required String id,
    required String name,
    required String alias,
    bool isUnmatched = false,
  }) {
    final isSelected = _selectedContactId == id;

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
          alias,
          style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
        ),
        subtitle: isUnmatched
            ? null
            : Text(name, style: AppTextStyles.caption),
        onTap: () {
          setState(() {
            _selectedContactId = id;
            _selectedContactName = name;
          });
        },
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
          onPressed: _startVerification,
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
    final verif = context.watch<VerificationProvider>();
    final req = verif.currentRequest;

    if (req == null) {
      return const Padding(
        padding: EdgeInsets.all(32.0),
        child: Center(child: CircularProgressIndicator()),
      );
    }

    final isDenied = req.isDenied;
    final isConfirmed = req.isConfirmed;
    final isExpired = req.isExpired;

    Color statusColor = AppColors.primaryGlow;
    String statusText = 'Pending responder confirmation...';
    IconData statusIcon = Icons.sync_rounded;

    if (isDenied) {
      statusColor = AppColors.danger;
      statusText = 'VERIFICATION DENIED: Contact confirmed they are NOT on a call with you!';
      statusIcon = Icons.dangerous_rounded;
    } else if (isConfirmed) {
      statusColor = AppColors.success;
      statusText = 'VERIFIED: Contact confirmed they are on this call with you.';
      statusIcon = Icons.check_circle_rounded;
    } else if (isExpired) {
      statusColor = AppColors.warning;
      statusText = 'EXPIRED: No response received within 45 seconds.';
      statusIcon = Icons.timer_off_rounded;
    }

    return Column(
      children: [
        const Text(
          'A secure challenge has been sent to the claimed contact\'s registered device. Ask them to confirm this match code:',
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
                req.matchCode,
                style: const TextStyle(
                  fontSize: 44,
                  fontWeight: FontWeight.w700,
                  fontFamily: 'monospace',
                  letterSpacing: 4,
                  color: AppColors.primaryGlow,
                ),
              ),
              const SizedBox(height: 6),
              Text(
                '${req.remainingSeconds}s remaining',
                style: TextStyle(
                  color: req.remainingSeconds < 15
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

        // Status banner
        Container(
          width: double.infinity,
          padding: const EdgeInsets.all(12),
          decoration: BoxDecoration(
            color: statusColor.withValues(alpha: 0.15),
            borderRadius: BorderRadius.circular(12),
            border: Border.all(color: statusColor),
          ),
          child: Row(
            children: [
              Icon(statusIcon, color: statusColor),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  statusText,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: isDenied ? FontWeight.w700 : FontWeight.w500,
                    color: statusColor,
                  ),
                ),
              ),
            ],
          ),
        ),
        const SizedBox(height: 16),

        // Responder Simulation Buttons (for hackathon demo)
        if (req.isPending) ...[
          Row(
            children: [
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.success,
                    side: const BorderSide(color: AppColors.success),
                  ),
                  onPressed: () {
                    verif.responderApprove(req.requestId);
                  },
                  child: const Text('Simulate Confirm'),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: OutlinedButton(
                  style: OutlinedButton.styleFrom(
                    foregroundColor: AppColors.danger,
                    side: const BorderSide(color: AppColors.danger),
                  ),
                  onPressed: () {
                    verif.responderDeny(req.requestId);
                  },
                  child: const Text('Simulate Deny'),
                ),
              ),
            ],
          ),
          const SizedBox(height: 14),
        ],

        PrimaryButton(
          label: isDenied || isConfirmed || isExpired
              ? 'Close'
              : 'Cancel Verification',
          variant: isDenied
              ? ButtonVariant.destructive
              : ButtonVariant.secondary,
          onPressed: () {
            verif.cancelCurrent();
            Navigator.pop(context);
          },
        ),
      ],
    );
  }
}
