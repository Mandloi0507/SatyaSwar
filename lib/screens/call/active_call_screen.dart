import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';

import '../../models/risk_band.dart';
import '../../services/audio_frame_builder.dart';
import '../../services/audio_player_service.dart';
import '../../services/wav_parser.dart';
import '../../services/window_planner.dart';
import '../../services/window_sender.dart';
import '../../theme/app_colors.dart';
import '../../theme/app_text_styles.dart';
import '../../utils/logger.dart';
import '../../utils/time_format.dart';
import '../../widgets/call/simulated_banner.dart';
import '../../widgets/common/app_scaffold.dart';
import '../../widgets/common/glass_card.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/risk_band_badge.dart';
import '../../widgets/common/status_chip.dart';
import '../../widgets/risk/evidence_quality_bar.dart';
import '../../widgets/risk/risk_meter.dart';
import '../../widgets/risk/score_timeline_chart.dart';
import '../verification/verify_caller_sheet.dart';

class ActiveCallScreen extends StatefulWidget {
  final Map<String, dynamic>? scenarioData;

  const ActiveCallScreen({super.key, this.scenarioData});

  @override
  State<ActiveCallScreen> createState() => _ActiveCallScreenState();
}

class _ActiveCallScreenState extends State<ActiveCallScreen> {
  // Audio Pipeline Components
  final AudioPlayerService _playerService = AudioPlayerService();
  WindowSender? _windowSender;
  WindowPlanner? _windowPlanner;
  WavData? _wavData;
  bool _isAudioReady = false;

  Timer? _callTimer;
  int _secondsElapsed = 0;

  // Real-time analysis state
  double _riskScore = 14.0;
  RiskBand _currentBand = RiskBand.low;
  final List<int> _timelineScores = [];
  int _windowsAnalysed = 0;
  double _speechSeconds = 0.0;
  int _lastLatencyMs = 320;
  String _latestAlert =
      'Acoustic parameters nominal. Analysing speech windows.';

  @override
  void initState() {
    super.initState();
    _startCallTimer();
    _initAudioPipeline();
  }

  Future<void> _initAudioPipeline() async {
    try {
      final scenarioId =
          widget.scenarioData?['scenarioId'] as String? ?? 'clone_ceo';
      final assetPath =
          'assets/audio/calls/${scenarioId == 'clone_ceo' ? 'clone_ceo_01.wav' : 'genuine_01.wav'}';

      AppLogger.d(
        'Initializing audio pipeline with $assetPath',
        'ActiveCallScreen',
      );

      // 1. Load audio asset bytes from rootBundle
      final ByteData data = await rootBundle.load(assetPath);
      final bytes = data.buffer.asUint8List();

      // 2. Parse and validate 16 kHz mono PCM16 format
      _wavData = WavParser.parse(bytes);
      _windowPlanner = WindowPlanner(totalSamples: _wavData!.totalSamples);

      AppLogger.d(
        'Parsed WAV: ${_wavData!.totalSamples} samples, ${_windowPlanner!.count} windows planned',
        'ActiveCallScreen',
      );

      // 3. Setup WindowSender synchronized with playback position
      _windowSender = WindowSender(
        positionStream: _playerService.positionStream,
        playerStateStream: _playerService.playerStateStream,
        pcm: _wavData!.samples,
        planner: _windowPlanner!,
        frameBuilder: const AudioFrameBuilder(),
        onFrame: _onAudioWindowEmitted,
      );

      // 4. Load audio into player and start playback
      await _playerService.loadAsset(assetPath);
      _windowSender!.start();
      await _playerService.play();

      if (mounted) {
        setState(() => _isAudioReady = true);
      }
    } catch (e, st) {
      AppLogger.e(
        'Failed to initialize audio pipeline',
        e,
        st,
        'ActiveCallScreen',
      );
      if (mounted) {
        setState(() {
          _latestAlert =
              'Demo audio clip unavailable. Using simulated speech stream.';
        });
      }
    }
  }

  void _onAudioWindowEmitted(Uint8List frame, int seq, DateTime sentAt) {
    if (!mounted) return;

    final scenarioId =
        widget.scenarioData?['scenarioId'] as String? ?? 'clone_ceo';
    int windowScore;

    // Deterministic progression mapped to scenario
    if (scenarioId == 'clone_ceo') {
      // Escalates to synthetic detection after initial windows
      if (seq < 2) {
        windowScore = 18 + seq * 4;
      } else if (seq < 4) {
        windowScore = 48 + seq * 5;
      } else {
        windowScore = 82 + (seq % 3) * 4;
      }
    } else {
      // Genuine call remains low risk
      windowScore = 10 + (seq % 3) * 3;
    }

    setState(() {
      _windowsAnalysed = seq + 1;
      _speechSeconds = (_windowsAnalysed * 1.75).clamp(0.0, 30.0);
      _lastLatencyMs = 280 + (seq * 15) % 90;
      _timelineScores.add(windowScore);
      _riskScore = windowScore.toDouble();

      if (windowScore >= 65) {
        _currentBand = RiskBand.high;
        _latestAlert = 'WARNING: High probability of synthetic voice cloning.';
      } else if (windowScore >= 35) {
        _currentBand = RiskBand.medium;
        _latestAlert =
            'Acoustic anomaly detected. Suspicious vocal pitch stability.';
      } else {
        _currentBand = RiskBand.low;
        _latestAlert = 'Acoustic parameters nominal. Natural vocal prosody.';
      }
    });

    AppLogger.d(
      'Window $seq emitted (${frame.length} bytes), score: $windowScore, band: ${_currentBand.name}',
      'ActiveCallScreen',
    );
  }

  void _startCallTimer() {
    _callTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() => _secondsElapsed++);
    });
  }

  @override
  void dispose() {
    _callTimer?.cancel();
    _windowSender?.dispose();
    _playerService.stop();
    _playerService.dispose();
    super.dispose();
  }

  void _handleEndCall() {
    _callTimer?.cancel();
    _windowSender?.dispose();
    _playerService.stop();

    context.pushReplacement(
      '/call/outcome',
      extra: {
        'scenarioId': widget.scenarioData?['scenarioId'] ?? 'clone_ceo',
        'claimedName': widget.scenarioData?['claimedName'] ?? 'Rakesh Sir',
        'peakRiskIndex': _riskScore.round(),
        'peakBand': _currentBand,
        'verificationStatus': 'Unverified',
        'finalOutcome': _currentBand == RiskBand.high
            ? 'Likely Impersonation'
            : 'Genuine Call',
      },
    );
  }

  void _openVerificationSheet() {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (ctx) => VerifyCallerSheet(
        claimedName:
            widget.scenarioData?['claimedName'] as String? ?? 'Rakesh Sir',
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final claimedName =
        widget.scenarioData?['claimedName'] as String? ?? 'Rakesh Sir';
    final durationStr = TimeFormat.formatDuration(
      Duration(seconds: _secondsElapsed),
    );

    return AppScaffold(
      safeArea: false,
      body: Stack(
        children: [
          // Background Gradient
          Container(
            decoration: const BoxDecoration(
              gradient: LinearGradient(
                colors: [Color(0xFF0F172A), AppColors.background],
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
              ),
            ),
          ),

          SafeArea(
            child: Column(
              children: [
                // 1. Mandatory Simulated Banner
                const SimulatedBanner(),

                // Connection Chip & Header
                Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20.0,
                    vertical: 10.0,
                  ),
                  child: Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      StatusChip(
                        label: _isAudioReady
                            ? 'Playback & Slicing Active'
                            : 'Initializing Audio...',
                        tone: _isAudioReady
                            ? StatusTone.success
                            : StatusTone.warning,
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 10,
                          vertical: 4,
                        ),
                        decoration: BoxDecoration(
                          color: AppColors.surfaceHigh,
                          borderRadius: BorderRadius.circular(10),
                          border: Border.all(color: AppColors.border),
                        ),
                        child: Text(
                          durationStr,
                          style: const TextStyle(
                            fontFamily: 'monospace',
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                            fontSize: 13,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),

                Expanded(
                  child: SingleChildScrollView(
                    padding: const EdgeInsets.symmetric(horizontal: 20.0),
                    child: Column(
                      children: [
                        const SizedBox(height: 8),

                        // Caller identity header
                        Text(
                          claimedName,
                          style: const TextStyle(
                            fontSize: 22,
                            fontWeight: FontWeight.w700,
                            color: AppColors.textPrimary,
                          ),
                        ),
                        const SizedBox(height: 4),
                        const Text(
                          'Active Call Simulation • 16 kHz Mono PCM16 Tap',
                          style: AppTextStyles.caption,
                        ),
                        const SizedBox(height: 16),

                        // 3. Central Risk Gauge
                        GlassCard(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 20,
                            vertical: 16,
                          ),
                          child: Column(
                            children: [
                              RiskMeter(
                                riskIndex: _riskScore,
                                band: _currentBand,
                              ),
                              const SizedBox(height: 12),
                              RiskBandBadge(band: _currentBand),
                              const SizedBox(height: 12),
                              Text(
                                _currentBand.fullTitle,
                                style: AppTextStyles.caption.copyWith(
                                  fontWeight: FontWeight.w500,
                                ),
                                textAlign: TextAlign.center,
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 14),

                        // Evidence Quality Bar
                        EvidenceQualityBar(
                          level: EvidenceLevel.good,
                          usableSpeechSec: _speechSeconds,
                        ),
                        const SizedBox(height: 14),

                        // 4. Acoustic Pipeline Diagnostics Row
                        Row(
                          children: [
                            _buildStatTile(
                              label: 'Windows',
                              value:
                                  '$_windowsAnalysed / ${_windowPlanner?.count ?? 9}',
                              icon: Icons.layers_rounded,
                            ),
                            const SizedBox(width: 10),
                            _buildStatTile(
                              label: 'Speech',
                              value: '${_speechSeconds.toStringAsFixed(1)}s',
                              icon: Icons.mic_none_rounded,
                            ),
                            const SizedBox(width: 10),
                            _buildStatTile(
                              label: 'Latency',
                              value: '${_lastLatencyMs}ms',
                              icon: Icons.speed_rounded,
                            ),
                          ],
                        ),
                        const SizedBox(height: 14),

                        // 5. Score Progression Chart
                        ScoreTimelineChart(windowScores: _timelineScores),
                        const SizedBox(height: 14),

                        // 6. Alert Message Strip
                        Container(
                          width: double.infinity,
                          padding: const EdgeInsets.all(12),
                          decoration: BoxDecoration(
                            color: _currentBand == RiskBand.high
                                ? AppColors.danger.withValues(alpha: 0.15)
                                : AppColors.surface,
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: _currentBand == RiskBand.high
                                  ? AppColors.danger
                                  : AppColors.border,
                            ),
                          ),
                          child: Row(
                            children: [
                              Icon(
                                _currentBand == RiskBand.high
                                    ? Icons.warning_rounded
                                    : Icons.info_outline_rounded,
                                size: 18,
                                color: _currentBand == RiskBand.high
                                    ? AppColors.danger
                                    : AppColors.primaryGlow,
                              ),
                              const SizedBox(width: 10),
                              Expanded(
                                child: Text(
                                  _latestAlert,
                                  style: TextStyle(
                                    fontSize: 12,
                                    color: _currentBand == RiskBand.high
                                        ? Colors.white
                                        : AppColors.textSecondary,
                                    fontWeight: _currentBand == RiskBand.high
                                        ? FontWeight.w600
                                        : FontWeight.w400,
                                  ),
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 20),
                      ],
                    ),
                  ),
                ),

                // 7. Bottom Action Bar: Verify Caller (Always visible) & End Call
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 20,
                    vertical: 14,
                  ),
                  decoration: const BoxDecoration(
                    color: AppColors.surface,
                    border: Border(
                      top: BorderSide(color: AppColors.border, width: 1),
                    ),
                  ),
                  child: Row(
                    children: [
                      // Verify Caller Primary Button
                      Expanded(
                        flex: 3,
                        child: PrimaryButton(
                          label: 'Verify Caller',
                          icon: Icons.verified_user_rounded,
                          onPressed: _openVerificationSheet,
                        ),
                      ),
                      const SizedBox(width: 12),
                      // End Call Destructive Button
                      Expanded(
                        flex: 2,
                        child: PrimaryButton(
                          label: 'End Call',
                          icon: Icons.call_end_rounded,
                          variant: ButtonVariant.destructive,
                          onPressed: _handleEndCall,
                        ),
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

  Widget _buildStatTile({
    required String label,
    required String value,
    required IconData icon,
  }) {
    return Expanded(
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 10, horizontal: 8),
        decoration: BoxDecoration(
          color: AppColors.surface,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: AppColors.border),
        ),
        child: Column(
          children: [
            Icon(icon, size: 16, color: AppColors.textSecondary),
            const SizedBox(height: 4),
            Text(
              value,
              style: const TextStyle(
                fontWeight: FontWeight.w700,
                fontSize: 13,
                color: AppColors.textPrimary,
              ),
            ),
            Text(
              label,
              style: const TextStyle(
                fontSize: 10,
                color: AppColors.textSecondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
