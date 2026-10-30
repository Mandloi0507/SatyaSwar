import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/primary_button.dart';

class AddContactScreen extends StatefulWidget {
  const AddContactScreen({super.key});

  @override
  State<AddContactScreen> createState() => _AddContactScreenState();
}

class _AddContactScreenState extends State<AddContactScreen>
    with SingleTickerProviderStateMixin {
  late TabController _tabController;
  final _codeController = TextEditingController();
  final _aliasController = TextEditingController();
  final _labelController = TextEditingController();

  final String _generatedInviteCode = 'K7M2-9QX4';
  final int _inviteExpiresSeconds = 600;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    _codeController.dispose();
    _aliasController.dispose();
    _labelController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(
        title: const Text('Add Trusted Contact'),
        bottom: TabBar(
          controller: _tabController,
          indicatorColor: AppColors.primary,
          labelColor: AppColors.primaryGlow,
          unselectedLabelColor: AppColors.textSecondary,
          tabs: const [
            Tab(text: 'Invite Contact', icon: Icon(Icons.qr_code_rounded)),
            Tab(text: 'Accept Invite', icon: Icon(Icons.link_rounded)),
          ],
        ),
      ),
      body: TabBarView(
        controller: _tabController,
        children: [
          // Tab 1: Invite someone
          _buildInviteTab(),
          // Tab 2: Accept an invite
          _buildAcceptTab(),
        ],
      ),
    );
  }

  Widget _buildInviteTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        children: [
          const Text(
            'Share this invite code or QR with your trusted contact. Once accepted, you will be linked for independent verification.',
            style: AppTextStyles.bodySecondary,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 28),

          // QR Display Card
          Container(
            padding: const EdgeInsets.all(24),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.border, width: 2),
            ),
            child: Column(
              children: [
                // Icon representation for QR placeholder
                Container(
                  width: 180,
                  height: 180,
                  color: Colors.white,
                  child: const Center(
                    child: Icon(
                      Icons.qr_code_2_rounded,
                      size: 160,
                      color: Colors.black87,
                    ),
                  ),
                ),
                const SizedBox(height: 12),
                Text(
                  _generatedInviteCode,
                  style: const TextStyle(
                    fontSize: 22,
                    fontWeight: FontWeight.w700,
                    color: Colors.black87,
                    letterSpacing: 3,
                    fontFamily: 'monospace',
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          Text(
            'Expires in ${_inviteExpiresSeconds ~/ 60} minutes',
            style: AppTextStyles.caption.copyWith(color: AppColors.warning),
          ),
          const SizedBox(height: 28),
          PrimaryButton(
            label: 'Share Invite Code',
            icon: Icons.share_rounded,
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(
                  content: Text('Invite code copied to clipboard'),
                ),
              );
            },
          ),
        ],
      ),
    );
  }

  Widget _buildAcceptTab() {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Enter the 8-character invite code provided by your contact, or scan their QR code.',
            style: AppTextStyles.bodySecondary,
          ),
          const SizedBox(height: 20),

          // Code entry field
          const Text('Invite Code', style: AppTextStyles.sectionHeader),
          const SizedBox(height: 8),
          Row(
            children: [
              Expanded(
                child: TextFormField(
                  controller: _codeController,
                  textCapitalization: TextCapitalization.characters,
                  style: AppTextStyles.monospaceCode.copyWith(fontSize: 18),
                  decoration: const InputDecoration(hintText: 'K7M2-9QX4'),
                ),
              ),
              const SizedBox(width: 12),
              IconButton.filled(
                style: IconButton.styleFrom(
                  backgroundColor: AppColors.surfaceHigh,
                  foregroundColor: AppColors.primaryGlow,
                  minimumSize: const Size(52, 52),
                  shape: RoundedRectangleBorder(
                    borderRadius: BorderRadius.circular(14),
                    side: const BorderSide(color: AppColors.border),
                  ),
                ),
                icon: const Icon(Icons.qr_code_scanner_rounded),
                onPressed: () => context.push('/contacts/scan'),
              ),
            ],
          ),
          const SizedBox(height: 20),

          const Text(
            'Contact Alias (Optional)',
            style: AppTextStyles.sectionHeader,
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _aliasController,
            style: const TextStyle(color: AppColors.textPrimary),
            decoration: const InputDecoration(
              hintText: 'e.g. Papa, Sunil Accountant',
            ),
          ),
          const SizedBox(height: 20),

          const Text('Relationship Label', style: AppTextStyles.sectionHeader),
          const SizedBox(height: 8),
          TextFormField(
            controller: _labelController,
            style: const TextStyle(color: AppColors.textPrimary),
            decoration: const InputDecoration(
              hintText: 'e.g. Family, Finance, Executive, College',
            ),
          ),
          const SizedBox(height: 32),

          PrimaryButton(
            label: 'Link Trusted Contact',
            icon: Icons.check_circle_outline_rounded,
            onPressed: () {
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Contact successfully linked')),
              );
              context.pop();
            },
          ),
        ],
      ),
    );
  }
}
