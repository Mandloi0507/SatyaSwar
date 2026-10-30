import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/primary_button.dart';

class ScanInviteScreen extends StatelessWidget {
  const ScanInviteScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(title: const Text('Scan Invite QR')),
      body: Padding(
        padding: const EdgeInsets.all(24.0),
        child: Column(
          children: [
            const Text(
              'Align the QR code provided by your contact within the frame below.',
              style: AppTextStyles.bodySecondary,
              textAlign: TextAlign.center,
            ),
            const SizedBox(height: 32),
            Expanded(
              child: Center(
                child: Container(
                  width: 260,
                  height: 260,
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(24),
                    border: Border.all(color: AppColors.primaryGlow, width: 2),
                  ),
                  child: Stack(
                    alignment: Alignment.center,
                    children: [
                      const Icon(
                        Icons.qr_code_scanner_rounded,
                        size: 120,
                        color: AppColors.primaryGlow,
                      ),
                      Positioned(
                        bottom: 16,
                        child: Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 12,
                            vertical: 4,
                          ),
                          decoration: BoxDecoration(
                            color: AppColors.surfaceHigh,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(color: AppColors.border),
                          ),
                          child: const Text(
                            'Scanning Active',
                            style: AppTextStyles.caption,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
            const SizedBox(height: 24),
            PrimaryButton(
              label: 'Simulate Scanned Code (K7M2-9QX4)',
              icon: Icons.check_rounded,
              variant: ButtonVariant.secondary,
              onPressed: () {
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text(
                      'Simulated QR scan: satyaswar:invite:K7M2-9QX4',
                    ),
                  ),
                );
                context.pop();
              },
            ),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}
