import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';

import '../../providers/contacts_provider.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/empty_state.dart';

class ContactsScreen extends StatelessWidget {
  const ContactsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    final contactsProvider = context.watch<ContactsProvider>();
    final contacts = contactsProvider.contacts;

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
      body: RefreshIndicator(
        onRefresh: () => contactsProvider.loadContacts(),
        color: AppColors.primaryGlow,
        backgroundColor: AppColors.surfaceHigh,
        child: ListView(
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

            if (contactsProvider.isLoading)
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(32.0),
                  child: CircularProgressIndicator(),
                ),
              )
            else if (contacts.isEmpty)
              EmptyState(
                icon: Icons.people_outline_rounded,
                title: 'No Trusted Contacts Yet',
                description:
                    'Add contacts via invite code or QR scan to enable independent verification.',
                actionLabel: 'Create Invite',
                onAction: () => context.push('/contacts/add'),
              )
            else
              ...contacts.map(
                (c) => Padding(
                  padding: const EdgeInsets.only(bottom: 10.0),
                  child: _buildContactTile(
                    context: context,
                    id: c.id,
                    name: c.name,
                    alias: c.alias,
                    phone: c.phoneNumber,
                    linkedDate: _formatDate(c.createdAt),
                  ),
                ),
              ),

            const SizedBox(height: 80), // Fab space
          ],
        ),
      ),
    );
  }

  String _formatDate(DateTime dt) {
    final diff = DateTime.now().difference(dt);
    if (diff.inDays == 0) return 'Linked today';
    if (diff.inDays == 1) return 'Linked yesterday';
    return 'Linked ${diff.inDays} days ago';
  }

  Widget _buildContactTile({
    required BuildContext context,
    required String id,
    required String name,
    required String alias,
    required String phone,
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
            Expanded(
              child: Text(
                alias,
                style: AppTextStyles.body.copyWith(fontWeight: FontWeight.w600),
              ),
            ),
            Container(
              padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
              decoration: BoxDecoration(
                color: AppColors.surfaceHigh,
                borderRadius: BorderRadius.circular(8),
                border: Border.all(color: AppColors.border),
              ),
              child: Text(
                name,
                style: const TextStyle(
                  fontSize: 11,
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
            Text(phone, style: AppTextStyles.caption),
            Text(
              linkedDate,
              style: const TextStyle(fontSize: 11, color: AppColors.textMuted),
            ),
          ],
        ),
        trailing: IconButton(
          icon: const Icon(
            Icons.delete_outline_rounded,
            color: AppColors.textMuted,
            size: 20,
          ),
          onPressed: () {
            context.read<ContactsProvider>().removeContact(id);
          },
        ),
      ),
    );
  }
}
