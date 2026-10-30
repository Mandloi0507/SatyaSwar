import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';

class ContactsScreen extends StatelessWidget {
  const ContactsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(
        title: const Text('Trusted Contacts'),
        actions: [
          IconButton(
            icon: const Icon(Icons.qr_code_scanner_rounded),
            tooltip: 'Scan Invite QR',
            onPressed: () => context.push('/contacts/scan'),
          ),
        ],
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: AppColors.primary,
        foregroundColor: Colors.white,
        icon: const Icon(Icons.person_add_rounded),
        label: const Text('Add Contact'),
        onPressed: () => context.push('/contacts/add'),
      ),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 16.0, vertical: 12.0),
        children: [
          Container(
            padding: const EdgeInsets.all(14),
            decoration: BoxDecoration(
              color: AppColors.surfaceHigh,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.border),
            ),
            child: const Row(
              children: [
                Icon(
                  Icons.verified_user_rounded,
                  color: AppColors.primaryGlow,
                  size: 24,
                ),
                SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Independent Verification Network: When an incoming voice is ambiguous, verification requests are routed to these contacts.',
                    style: TextStyle(
                      color: AppColors.textSecondary,
                      fontSize: 12,
                      height: 1.35,
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 16),
          _buildContactTile(
            name: 'Priyanka Sharma',
            alias: 'Priti',
            label: 'Family',
            code: 'U102',
            linkedDate: 'Linked 2 days ago',
          ),
          const SizedBox(height: 10),
          _buildContactTile(
            name: 'Rakesh Verma',
            alias: 'Rakesh Sir',
            label: 'Executive',
            code: 'U204',
            linkedDate: 'Linked 1 week ago',
          ),
          const SizedBox(height: 10),
          _buildContactTile(
            name: 'Sunil Mehta',
            alias: 'Sunil (Accountant)',
            label: 'Finance',
            code: 'U309',
            linkedDate: 'Linked 3 weeks ago',
          ),
          const SizedBox(height: 80), // Fab space
        ],
      ),
    );
  }

  Widget _buildContactTile({
    required String name,
    required String alias,
    required String label,
    required String code,
    required String linkedDate,
  }) {
    return Container(
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: AppColors.border),
      ),
      child: ListTile(
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
        leading: CircleAvatar(
          backgroundColor: AppColors.surfaceHigh,
          child: Text(
            alias.isNotEmpty ? alias[0] : name[0],
            style: const TextStyle(
              color: AppColors.primaryGlow,
              fontWeight: FontWeight.w700,
            ),
          ),
        ),
        title: Row(
          children: [
            Text(
              alias,
              style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(width: 8),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: Text(
                label,
                style: const TextStyle(
                  fontSize: 10,
                  color: AppColors.textSecondary,
                ),
              ),
            ),
          ],
        ),
        subtitle: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            const SizedBox(height: 2),
            Text('$name • ID: $code', style: AppTextStyles.caption),
            Text(
              linkedDate,
              style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
            ),
          ],
        ),
        trailing: const Icon(
          Icons.shield_rounded,
          color: AppColors.riskLow,
          size: 20,
        ),
      ),
    );
  }
}
