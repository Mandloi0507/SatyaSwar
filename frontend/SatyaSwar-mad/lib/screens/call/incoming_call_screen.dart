import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../widgets/call/simulated_banner.dart';
import '../../widgets/common/app_scaffold.dart';

class IncomingCallScreen extends StatefulWidget {
  final Map<String, dynamic>? scenarioData;

  const IncomingCallScreen({super.key, this.scenarioData});

  @override
  State<IncomingCallScreen> createState() => _IncomingCallScreenState();
}

class _IncomingCallScreenState extends State<IncomingCallScreen>
    with SingleTickerProviderStateMixin {
  late AnimationController _pulseController;

  @override
  void initState() {
    super.initState();
    _pulseController = AnimationController(
      vsync: this,
      duration: const Duration(seconds: 2),
    )..repeat(reverse: true);
  }

  @override
  void dispose() {
    _pulseController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final claimedName =
        widget.scenarioData?['claimedName'] as String? ?? 'Rakesh Sir';
    final callerNumber =
        widget.scenarioData?['callerNumber'] as String? ?? 'Unknown Caller';

    return AppScaffold(
      safeArea: false,
      body: Stack(
        children: [
          // Background Gradient
          Container(
            decoration: const BoxDecoration(
              gradient: RadialGradient(
                center: Alignment(0, -0.2),
                radius: 1.2,
                colors: [Color(0xFF16233B), AppColors.background],
              ),
            ),
          ),

          SafeArea(
            child: Column(
              children: [
                // 1. Mandatory Simulated Banner
                const SimulatedBanner(),
                const SizedBox(height: 32),

                // Call Type Header
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 14,
                    vertical: 6,
                  ),
                  decoration: BoxDecoration(
                    color: AppColors.surfaceHigh,
                    borderRadius: BorderRadius.circular(20),
                    border: Border.all(color: AppColors.border),
                  ),
                  child: const Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.call_rounded,
                        size: 14,
                        color: AppColors.primaryGlow,
                      ),
                      SizedBox(width: 6),
                      Text(
                        'SIMULATED INCOMING CALL',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w700,
                          color: AppColors.primaryGlow,
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // Caller identity
                Text(
                  claimedName,
                  style: const TextStyle(
                    fontSize: 28,
                    fontWeight: FontWeight.w700,
                    color: AppColors.textPrimary,
                  ),
                ),
                const SizedBox(height: 6),
                Text(
                  callerNumber,
                  style: AppTextStyles.bodySecondary.copyWith(fontSize: 16),
                ),
                const SizedBox(height: 8),
                const Text(
                  'Ringing...',
                  style: TextStyle(
                    color: AppColors.primaryGlow,
                    fontSize: 13,
                    fontWeight: FontWeight.w500,
                  ),
                ),

                const Spacer(),

                // Pulsing Avatar
                AnimatedBuilder(
                  animation: _pulseController,
                  builder: (context, child) {
                    final scale = 1.0 + (_pulseController.value * 0.08);
                    final opacity = 0.2 + (_pulseController.value * 0.2);
                    return Stack(
                      alignment: Alignment.center,
                      children: [
                        Transform.scale(
                          scale: scale * 1.3,
                          child: Container(
                            width: 130,
                            height: 130,
                            decoration: BoxDecoration(
                              shape: BoxShape.circle,
                              color: AppColors.primary.withValues(
                                alpha: opacity,
                              ),
                            ),
                          ),
                        ),
                        Container(
                          width: 120,
                          height: 120,
                          decoration: BoxDecoration(
                            shape: BoxShape.circle,
                            color: AppColors.surfaceHigh,
                            border: Border.all(
                              color: AppColors.primaryGlow,
                              width: 2,
                            ),
                          ),
                          child: Center(
                            child: Text(
                              claimedName.isNotEmpty ? claimedName[0] : '?',
                              style: const TextStyle(
                                fontSize: 44,
                                fontWeight: FontWeight.w700,
                                color: AppColors.primaryGlow,
                              ),
                            ),
                          ),
                        ),
                      ],
                    );
                  },
                ),

                const Spacer(),

                // Accept & Decline Round Controls
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 48.0,
                    vertical: 36.0,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      // Decline Button (Red)
                      Column(
                        children: [
                          GestureDetector(
                            onTap: () => context.pop(),
                            child: Container(
                              width: 72,
                              height: 72,
                              decoration: const BoxDecoration(
                                shape: BoxShape.circle,
                                color: AppColors.danger,
                                boxShadow: [
                                  BoxShadow(
                                    color: Color(0x66DC2626),
                                    blurRadius: 16,
                                    spreadRadius: 2,
                                  ),
                                ],
                              ),
                              child: const Icon(
                                Icons.call_end_rounded,
                                color: Colors.white,
                                size: 32,
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          const Text('Decline', style: AppTextStyles.caption),
                        ],
                      ),

                      // Accept Button (Green)
                      Column(
                        children: [
                          GestureDetector(
                            onTap: () {
                              context.pushReplacement(
                                '/call/active',
                                extra: widget.scenarioData,
                              );
                            },
                            child: Container(
                              width: 72,
                              height: 72,
                              decoration: const BoxDecoration(
                                shape: BoxShape.circle,
                                color: AppColors.success,
                                boxShadow: [
                                  BoxShadow(
                                    color: Color(0x6616A34A),
                                    blurRadius: 16,
                                    spreadRadius: 2,
                                  ),
                                ],
                              ),
                              child: const Icon(
                                Icons.call_rounded,
                                color: Colors.white,
                                size: 32,
                              ),
                            ),
                          ),
                          const SizedBox(height: 10),
                          const Text('Accept', style: AppTextStyles.caption),
                        ],
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
