import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../models/scenario.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/common/app_scaffold.dart';

class ScenarioPickerScreen extends StatefulWidget {
  const ScenarioPickerScreen({super.key});

  @override
  State<ScenarioPickerScreen> createState() => _ScenarioPickerScreenState();
}

class _ScenarioPickerScreenState extends State<ScenarioPickerScreen> {
  List<Scenario> _scenarios = Scenario.defaultScenarios;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadScenarios();
  }

  Future<void> _loadScenarios() async {
    final list = await Scenario.loadAll();
    if (mounted) {
      setState(() {
        _scenarios = list;
        _isLoading = false;
      });
    }
  }

  IconData _iconForScenario(String id) {
    switch (id) {
      case 'clone_ceo':
        return Icons.warning_amber_rounded;
      case 'genuine_family':
        return Icons.check_circle_outline_rounded;
      case 'noisy_call':
        return Icons.volume_down_rounded;
      case 'short_insufficient':
        return Icons.help_outline_rounded;
      default:
        return Icons.phone_in_talk_rounded;
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      appBar: AppBar(title: const Text('Select Simulation Scenario')),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.symmetric(
                horizontal: 20.0,
                vertical: 16.0,
              ),
              children: [
                // Direction Badge (Inbound Caller Simulation)
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 10,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surface,
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: const Row(
                    children: [
                      Icon(
                        Icons.call_received_rounded,
                        color: AppColors.primaryGlow,
                        size: 20,
                      ),
                      SizedBox(width: 10),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Simulation Mode: Inbound Caller',
                              style: TextStyle(
                                color: AppColors.textPrimary,
                                fontWeight: FontWeight.w700,
                                fontSize: 13,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Demonstrating real-time detection on incoming voice calls',
                              style: TextStyle(
                                color: AppColors.textSecondary,
                                fontSize: 11,
                              ),
                            ),
                          ],
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
                ..._scenarios.map(_buildScenarioCard),
              ],
            ),
    );
  }

  Widget _buildScenarioCard(Scenario scenario) {
    final isDanger = scenario.isDanger;
    final icon = _iconForScenario(scenario.id);
    final durationSec = (scenario.durationMs / 1000).toStringAsFixed(1);

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
              'scenarioId': scenario.id,
              'claimedName': scenario.claimedName,
              'callerNumber': scenario.callerNumber,
              'audioAsset': scenario.audioAsset,
              'durationMs': scenario.durationMs,
              'description': scenario.description,
              'expectedBand': scenario.expectedBand,
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
                      icon,
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
                          scenario.title,
                          style: AppTextStyles.sectionHeader,
                        ),
                        const SizedBox(height: 2),
                        Text(
                          'Claimed: ${scenario.claimedName} • ${durationSec}s',
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
                scenario.description,
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
                      'Expected: ${scenario.expectedBand}',
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
