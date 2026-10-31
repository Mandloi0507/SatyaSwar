import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:provider/provider.dart';
import 'package:qr_flutter/qr_flutter.dart';

import '../../providers/auth_provider.dart';
import '../../providers/contacts_provider.dart';
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
  final _nameController = TextEditingController();
  final _aliasController = TextEditingController();

  String _generatedInviteCode = 'SW-9482';
  bool _isGeneratingCode = false;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
    _generateFreshCode();
  }

  Future<void> _generateFreshCode() async {
    setState(() => _isGeneratingCode = true);
    final auth = context.read<AuthProvider>();
    final contacts = context.read<ContactsProvider>();
    final code = await contacts.generateInviteCode(
      auth.currentUser?.displayName ?? 'User',
    );
    if (!mounted) return;
    setState(() {
      _generatedInviteCode = code;
      _isGeneratingCode = false;
    });
  }

  @override
  void dispose() {
    _tabController.dispose();
    _codeController.dispose();
    _nameController.dispose();
    _aliasController.dispose();
    super.dispose();
  }

  void _handleAcceptInvite() async {
    final code = _codeController.text.trim();
    final name = _nameController.text.trim();
    final alias = _aliasController.text.trim();

    if (code.isEmpty || name.isEmpty) {
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('Please enter both invite code and contact name'),
          backgroundColor: AppColors.danger,
        ),
      );
      return;
    }

    final contacts = context.read<ContactsProvider>();
    final success = await contacts.acceptInviteCode(
      code: code,
      contactName: name,
      alias: alias.isNotEmpty ? alias : name,
    );

    if (!mounted) return;

    if (success) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Trusted contact "$name" successfully linked!'),
          backgroundColor: AppColors.success,
        ),
      );
      context.pop();
    } else {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(contacts.errorMessage ?? 'Failed to accept invite'),
          backgroundColor: AppColors.danger,
        ),
      );
    }
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
          _buildInviteTab(),
          _buildAcceptTab(),
        ],
      ),
    );
  }

  Widget _buildInviteTab() {
    final qrData = 'satyaswar://invite?code=$_generatedInviteCode';

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
            decoration: BoxDecoration(
              color: AppColors.primary.withValues(alpha: 0.15),
              borderRadius: BorderRadius.circular(8),
              border: Border.all(color: AppColors.primary.withValues(alpha: 0.3)),
            ),
            child: const Text(
              'DEMO INVITE CODE • Local Simulated Verification',
              style: TextStyle(
                fontSize: 10,
                fontWeight: FontWeight.w700,
                color: AppColors.primaryGlow,
                letterSpacing: 0.5,
              ),
            ),
          ),
          const SizedBox(height: 12),
          const Text(
            'Share this invite code or QR with your trusted contact. Once accepted, you will be linked for independent verification.',
            style: AppTextStyles.bodySecondary,
            textAlign: TextAlign.center,
          ),
          const SizedBox(height: 24),

          // QR Display Card
          Container(
            padding: const EdgeInsets.all(20),
            decoration: BoxDecoration(
              color: Colors.white,
              borderRadius: BorderRadius.circular(20),
              border: Border.all(color: AppColors.border, width: 2),
            ),
            child: Column(
              children: [
                if (_isGeneratingCode)
                  const SizedBox(
                    width: 180,
                    height: 180,
                    child: Center(child: CircularProgressIndicator()),
                  )
                else
                  SizedBox(
                    width: 180,
                    height: 180,
                    child: QrImageView(
                      data: qrData,
                      version: QrVersions.auto,
                      size: 180.0,
                      backgroundColor: Colors.white,
                      eyeStyle: const QrEyeStyle(
                        eyeShape: QrEyeShape.square,
                        color: Color(0xFF0A0F1C),
                      ),
                      dataModuleStyle: const QrDataModuleStyle(
                        dataModuleShape: QrDataModuleShape.square,
                        color: Color(0xFF0A0F1C),
                      ),
                    ),
                  ),
                const SizedBox(height: 16),
                Text(
                  _generatedInviteCode,
                  style: const TextStyle(
                    fontSize: 24,
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
            'Expires in 10 minutes (Simulated)',
            style: AppTextStyles.caption.copyWith(color: AppColors.warning),
          ),
          const SizedBox(height: 24),
          Row(
            children: [
              Expanded(
                child: PrimaryButton(
                  label: 'Copy Code',
                  variant: ButtonVariant.secondary,
                  icon: Icons.copy_rounded,
                  onPressed: () async {
                    await Clipboard.setData(
                      ClipboardData(text: _generatedInviteCode),
                    );
                    if (!mounted) return;
                    ScaffoldMessenger.of(context).showSnackBar(
                      SnackBar(
                        content: Text(
                          'Invite code "$_generatedInviteCode" copied to clipboard!',
                        ),
                        backgroundColor: AppColors.success,
                        duration: const Duration(seconds: 2),
                      ),
                    );
                  },
                ),
              ),
              const SizedBox(width: 12),
              Expanded(
                child: PrimaryButton(
                  label: 'New Code',
                  icon: Icons.refresh_rounded,
                  onPressed: _generateFreshCode,
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildAcceptTab() {
    final contacts = context.watch<ContactsProvider>();

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Enter the invite code provided by your contact, or scan their QR code.',
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
                  decoration: const InputDecoration(hintText: 'SW-9482'),
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
                onPressed: () async {
                  final scanned = await context.push<String>('/contacts/scan');
                  if (scanned != null && mounted) {
                    _codeController.text = scanned;
                  }
                },
              ),
            ],
          ),
          const SizedBox(height: 20),

          const Text('Contact Full Name', style: AppTextStyles.sectionHeader),
          const SizedBox(height: 8),
          TextFormField(
            controller: _nameController,
            style: const TextStyle(color: AppColors.textPrimary),
            decoration: const InputDecoration(
              hintText: 'e.g. Rakesh Verma',
            ),
          ),
          const SizedBox(height: 20),

          const Text(
            'Contact Alias / Relationship (Optional)',
            style: AppTextStyles.sectionHeader,
          ),
          const SizedBox(height: 8),
          TextFormField(
            controller: _aliasController,
            style: const TextStyle(color: AppColors.textPrimary),
            decoration: const InputDecoration(
              hintText: 'e.g. CEO, Papa, Tech Lead',
            ),
          ),
          const SizedBox(height: 32),

          PrimaryButton(
            label: 'Link Trusted Contact',
            icon: Icons.check_circle_outline_rounded,
            isLoading: contacts.isLoading,
            onPressed: _handleAcceptInvite,
          ),
        ],
      ),
    );
  }
}
