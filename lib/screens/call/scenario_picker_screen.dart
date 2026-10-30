import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';

class ScenarioPickerScreen extends StatefulWidget {
  const ScenarioPickerScreen({super.key});

  @override
  State<ScenarioPickerScreen> createState() => _ScenarioPickerScreenState();
}

class _ScenarioPickerScreenState extends State<ScenarioPickerScreen> {
  String _selectedDirection = 'incoming';

  final List<Map<String, dynamic>> _scenarios = [
    {
      'id': 'clone_ceo',
      'title': 'Cloned CEO Voice (Impersonation)',
      'claimedName': 'Rakesh Sir',
      'callerNumber': 'Unknown Caller',
      'duration': '21.0s (11 windows)',
      'expectedBand': 'High Risk / Synthetic',
      'description': 'High-urgency synthetic voice impersonating executive leadership requesting an urgent fund transfer.',
      'icon': Icons.warning_rounded,
      'isDanger': true,
    },
    {
      'id': 'genuine_family',
      'title': 'Genuine Family Call',
      'claimedName': 'Priyanka',
      'callerNumber': '+91 98xxxxxx01',
      'duration': '17.5s (9 windows)',
      'expectedBand': 'Low Risk / Genuine',
      'description': 'Natural biological voice from known family contact with standard prosody and speech rhythms.',
      'icon': Icons.check_circle_outline_rounded,
      'isDanger': false,
    },
    {
      'id': 'noisy_call',
      'title': 'Noisy Background Scenario',
      'claimedName': 'Delivery Agent',
      'callerNumber': '+91 91xxxxxx42',
      'duration': '17.5s (9 windows)',
      'expectedBand': 'Medium / Adaptive Quality',
      'description': 'Heavy ambient background noise challenging acoustic feature extraction.',
      'icon': Icons.volume_down_rounded,
      'isDanger': false,
    },
    {
      'id': 'short_insufficient',
      'title': 'Degraded Audio Sample',
      'claimedName': 'Bank Officer',
      'callerNumber': '+91 80xxxxxx99',
      'duration': '17.5s (Sparse speech)',
      'expectedBand': 'Insufficient Evidence',
      'description': 'Refusal to guess under inadequate speech duration or acoustic confidence.',
      'icon': Icons.help_outline_rounded,
      'isDanger': false,
    },
  ];

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(title: const Text('Select Simulation Scenario')),
      body: ListView(
        padding: const EdgeInsets.symmetric(horizontal: 20.0, vertical: 16.0),
        children: [
          // Direction Selector
          Container(
            padding: const EdgeInsets.all(4),
            decoration: BoxDecoration(
              color: AppColors.surface,
              borderRadius: BorderRadius.circular(14),
              border: Border.all(color: AppColors.border),
            ),
            child: Row(
              children: [
                Expanded(
                  child: GestureDetector(
                    onTap: () =>
                        setState(() => _selectedDirection = 'incoming'),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: _selectedDirection == 'incoming'
                            ? AppColors.primary
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        'Incoming Call',
                        style: TextStyle(
                          color: _selectedDirection == 'incoming'
                              ? Colors.white
                              : AppColors.textSecondary,
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ),
                ),
                Expanded(
                  child: GestureDetector(
                    onTap: () =>
                        setState(() => _selectedDirection = 'outgoing'),
                    child: Container(
                      padding: const EdgeInsets.symmetric(vertical: 10),
                      decoration: BoxDecoration(
                        color: _selectedDirection == 'outgoing'
                            ? AppColors.primary
                            : Colors.transparent,
                        borderRadius: BorderRadius.circular(10),
                      ),
                      alignment: Alignment.center,
                      child: Text(
                        'Outgoing Call',
                        style: TextStyle(
                          color: _selectedDirection == 'outgoing'
                              ? Colors.white
                              : AppColors.textSecondary,
                          fontWeight: FontWeight.w600,
                          fontSize: 13,
                        ),
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 20),
          const Text(
            'Select a scenario to launch the simulated call experience:',
            style: AppTextStyles.bodySecondary,
          ),
          const SizedBox(height: 16),

          ..._scenarios.map((scenario) => _buildScenarioCard(scenario)),
        ],
      ),
    );
  }

  Widget _buildScenarioCard(Map<String, dynamic> scenario) {
    final isDanger = scenario['isDanger'] as bool;

    return Container(
      margin: const EdgeInsets.only(bottom: 14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        borderRadius: BorderRadius.circular(18),
        border: Border.all(
          color: isDanger
              ? AppColors.danger.withValues(alpha: 0.4)
              : AppColors.border,
          width: isDanger ? 1.5 : 1.0,
        ),
      ),
      child: InkWell(
        borderRadius: BorderRadius.circular(18),
        onTap: () {
          context.push(
            '/call/incoming',
            extra: {
              'scenarioId': scenario['id'],
              'claimedName': scenario['claimedName'],
              'callerNumber': scenario['callerNumber'],
              'direction': _selectedDirection,
            },
          );
        },
        child: Padding(
          padding: const EdgeInsets.all(16.0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(10),
                    decoration: BoxDecoration(
                      color: isDanger
                          ? AppColors.danger.withValues(alpha: 0.15)
                          : AppColors.primary.withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(12),
                    ),
                    child: Icon(
                      scenario['icon'] as IconData,
                      color: isDanger
                          ? AppColors.danger
                          : AppColors.primaryGlow,
                      size: 22,
                    ),
                  ),
                  const SizedBox(width: 14),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          scenario['title'] as String,
                          style: AppTextStyles.sectionHeader,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Claimed: ${scenario['claimedName']} • ${scenario['duration']}',
                          style: AppTextStyles.caption.copyWith(
                            color: AppColors.primaryGlow,
                          ),
                        ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              Text(
                scenario['description'] as String,
                style: AppTextStyles.bodySecondary.copyWith(fontSize: 13),
              ),
              const SizedBox(height: 12),
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    padding: const EdgeInsets.symmetric(
                      horizontal: 8,
                      vertical: 3,
                    ),
                    decoration: BoxDecoration(
                      color: AppColors.surfaceHigh,
                      borderRadius: BorderRadius.circular(8),
                      border: Border.all(color: AppColors.border),
                    ),
                    child: Text(
                      'Expected: ${scenario['expectedBand']}',
                      style: const TextStyle(
                        fontSize: 11,
                        color: AppColors.textSecondary,
                      ),
                    ),
                  ),
                  const Row(
                    children: [
                      Text(
                        'Launch',
                        style: TextStyle(
                          color: AppColors.primaryGlow,
                          fontSize: 13,
                          fontWeight: FontWeight.w600,
                        ),
                      ),
                      SizedBox(width: 4),
                      Icon(
                        Icons.arrow_forward_rounded,
                        size: 16,
                        color: AppColors.primaryGlow,
                      ),
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
