import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:go_router/go_router.dart';
import 'package:just_audio/just_audio.dart';
import 'package:provider/provider.dart';

import '../../models/call_history_record.dart';
import '../../models/risk_band.dart';
import '../../models/scenario.dart';
import '../../providers/call_history_provider.dart';
import '../../providers/risk_monitor_provider.dart';
import '../../providers/settings_provider.dart';
import '../../services/alert_service.dart';
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
  AlertService? _alertService;
  WindowSender? _windowSender;
  WindowPlanner? _windowPlanner;
  WavData? _wavData;
  bool _isAudioReady = false;
  String? _audioErrorMessage;
  Duration _playbackPosition = Duration.zero;
  Duration? _audioTotalDuration;
  StreamSubscription<Duration>? _positionSub;
  StreamSubscription<PlayerState>? _playerStateSub;

  Timer? _callTimer;
  int _secondsElapsed = 0;

  @override
  void initState() {
    super.initState();
    // Call timer begins ONLY when playback actually begins, not at initial widget mount
    _initAudioPipeline();
  }

  Future<void> _initAudioPipeline() async {
    try {
      final scenarioId =
          widget.scenarioData?['scenarioId'] as String? ?? 'clone_ceo';
      String assetPath = widget.scenarioData?['audioAsset'] as String? ?? '';
      if (assetPath.isEmpty) {
        assetPath = Scenario.assetForScenarioId(scenarioId);
      }

      AppLogger.d(
        'Initializing audio pipeline with $assetPath (scenario: $scenarioId)',
        'ActiveCallScreen',
      );

      // 1. Initialize AlertService with volume ducking
      _alertService = AlertService(audioPlayerService: _playerService);
      final riskMonitor = context.read<RiskMonitorProvider>();
      riskMonitor.attachAlertService(_alertService!);

      final settings = context.read<SettingsProvider>();
      final callId = 'call_${DateTime.now().millisecondsSinceEpoch}';
      try {
        await riskMonitor.startAnalysis(
          callId: callId,
          scenarioId: scenarioId,
          isMockMode: settings.isMockMode,
          serverBaseAddress: settings.serverAddress,
        );
      } catch (e) {
        AppLogger.w('startAnalysis initial connection warning: $e', 'ActiveCallScreen');
      }

      // 2. Load audio asset bytes from rootBundle
      final ByteData data = await rootBundle.load(assetPath);
      final bytes = data.buffer.asUint8List();

      // 3. Parse and validate 16 kHz mono PCM16 format
      _wavData = WavParser.parse(bytes);
      _windowPlanner = WindowPlanner(totalSamples: _wavData!.totalSamples);

      AppLogger.d(
        'Parsed WAV: ${_wavData!.totalSamples} samples, ${_windowPlanner!.count} windows planned',
        'ActiveCallScreen',
      );

      // 4. Setup WindowSender synchronized with playback position
      _windowSender = WindowSender(
        positionStream: _playerService.positionStream,
        playerStateStream: _playerService.playerStateStream,
        pcm: _wavData!.samples,
        planner: _windowPlanner!,
        frameBuilder: const AudioFrameBuilder(),
        onFrame: _onAudioWindowEmitted,
      );

      // Track playback position for live display
      _positionSub?.cancel();
      _positionSub = _playerService.positionStream.listen((pos) {
        if (!mounted) return;
        setState(() => _playbackPosition = pos);
        // Secondary safeguard: if position advances and timer hasn't started yet, start it
        if (pos > Duration.zero && (_callTimer == null || !_callTimer!.isActive)) {
          _startCallTimer();
        }
      });

      // Observe playerStateStream: Do NOT mark audio as ready merely because asset loaded
      _playerStateSub?.cancel();
      _playerStateSub = _playerService.playerStateStream.listen((state) {
        if (!mounted) return;
        AppLogger.d(
          'PlayerState: processingState=${state.processingState}, playing=${state.playing}',
          'ActiveCallScreen',
        );

        // Mark ready only when player actually reaches ready state
        if (state.processingState == ProcessingState.ready ||
            (state.playing && state.processingState != ProcessingState.idle)) {
          if (!_isAudioReady) {
            setState(() {
              _isAudioReady = true;
              _audioErrorMessage = null;
            });
          }
        }

        // Start call timer ONLY when playback actually begins
        if (state.playing &&
            (state.processingState == ProcessingState.ready ||
                state.processingState == ProcessingState.buffering)) {
          if (_callTimer == null || !_callTimer!.isActive) {
            _startCallTimer();
          }
        }

        // Stop timer when playback completes
        if (state.processingState == ProcessingState.completed) {
          _stopCallTimer();
          AppLogger.d('Audio playback completed: call timer stopped', 'ActiveCallScreen');
        }
      }, onError: (Object err) {
        if (!mounted) return;
        _stopCallTimer();
        setState(() {
          _isAudioReady = false;
          _audioErrorMessage = 'Audio playback stream error: $err';
        });
      });

      // 5. Load audio into player
      final dur = await _playerService.loadAsset(assetPath);
      _windowSender!.start();

      if (mounted) {
        setState(() {
          _audioTotalDuration = dur;
          _audioErrorMessage = null;
        });
      }

      // Start playback non-blocking so call UI runs concurrently with playback
      unawaited(_playerService.play().catchError((Object e, StackTrace st) {
        AppLogger.e('Playback execution error', e, st, 'ActiveCallScreen');
        if (mounted) {
          _stopCallTimer();
          setState(() {
            _isAudioReady = false;
            _audioErrorMessage = 'Playback execution error: $e';
          });
        }
      }));
    } catch (e, st) {
      AppLogger.e(
        'Failed to initialize audio pipeline',
        e,
        st,
        'ActiveCallScreen',
      );
      if (mounted) {
        _stopCallTimer();
        setState(() {
          _isAudioReady = false;
          _audioErrorMessage = 'Audio engine error: $e';
        });
      }
    }
  }

  void _onAudioWindowEmitted(Uint8List frame, int seq, DateTime sentAt) {
    if (!mounted) return;
    context.read<RiskMonitorProvider>().ingestFrame(frame);
  }

  void _startCallTimer() {
    _callTimer?.cancel();
    _callTimer = Timer.periodic(const Duration(seconds: 1), (timer) {
      if (!mounted) return;
      setState(() => _secondsElapsed++);
    });
  }

  void _stopCallTimer() {
    _callTimer?.cancel();
    _callTimer = null;
  }

  Future<void> _retryAudio() async {
    _stopCallTimer();
    await _playerStateSub?.cancel();
    await _positionSub?.cancel();
    await _windowSender?.dispose();
    await _playerService.stop();
    if (mounted) {
      setState(() {
        _secondsElapsed = 0;
        _playbackPosition = Duration.zero;
        _isAudioReady = false;
        _audioErrorMessage = null;
      });
    }
    await _initAudioPipeline();
  }

  @override
  void dispose() {
    _stopCallTimer();
    _playerStateSub?.cancel();
    _positionSub?.cancel();
    _windowSender?.dispose();
    _playerService.stop();
    _playerService.dispose();
    _alertService?.dispose();
    super.dispose();
  }

  void _handleEndCall() {
    _stopCallTimer();
    _playerStateSub?.cancel();
    _positionSub?.cancel();
    _windowSender?.dispose();
    _playerService.stop();

    final riskMonitor = context.read<RiskMonitorProvider>();
    final history = context.read<CallHistoryProvider>();
    final settings = context.read<SettingsProvider>();

    final scenarioId =
        widget.scenarioData?['scenarioId'] as String? ?? 'clone_ceo';
    final claimedName =
        widget.scenarioData?['claimedName'] as String? ?? 'Rakesh Sir';
    final peakRisk = riskMonitor.peakScore.round();
    final peakBand = riskMonitor.currentBand;

    // Server-reported outcome: Client never generates final authenticity verdicts independently
    final serverOutcome = settings.isMockMode
        ? 'Simulated session ended (Offline Mock Evaluation)'
        : (riskMonitor.latestAlertMessage.isNotEmpty
            ? riskMonitor.latestAlertMessage
            : 'Analysis session ended');

    // Record scores-only call history (never stores raw audio or transcripts)
    final record = CallHistoryRecord(
      id: 'call_${DateTime.now().millisecondsSinceEpoch}',
      callerName: claimedName,
      callerNumber:
          widget.scenarioData?['callerNumber'] as String? ?? '+91 98200 11223',
      timestamp: DateTime.now(),
      durationSeconds: _secondsElapsed,
      peakRiskScore: peakRisk,
      peakRiskBand: peakBand,
      evidenceQuality: riskMonitor.evidenceQuality,
      verificationStatus: 'unverified',
      finalOutcome: serverOutcome,
      timelineScores: List.of(riskMonitor.timelineScores),
    );

    history.addRecord(record);

    context.pushReplacement(
      '/call/outcome',
      extra: {
        'scenarioId': scenarioId,
        'claimedName': claimedName,
        'peakRiskIndex': peakRisk,
        'peakBand': peakBand,
        'verificationStatus': 'Unverified',
        'isMock': settings.isMockMode,
        'serverReportedOutcome': serverOutcome,
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
    final riskMonitor = context.watch<RiskMonitorProvider>();
    final claimedName =
        widget.scenarioData?['claimedName'] as String? ?? 'Rakesh Sir';
    final durationStr = TimeFormat.formatDuration(
      Duration(seconds: _secondsElapsed),
    );

    final isDanger = riskMonitor.currentBand == RiskBand.high;
    final isAmber = riskMonitor.currentBand == RiskBand.medium;

    return AppScaffold(
      body: Column(
        children: [
          // 1. Mandatory Simulated Call Disclaimer Banner
          const SimulatedBanner(),

          // 1b. Mock Engine Indicator
          if (context.watch<SettingsProvider>().isMockMode)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
              color: AppColors.primary.withValues(alpha: 0.12),
              alignment: Alignment.center,
              child: const Text(
                'SIMULATED ANALYSIS (OFFLINE MOCK ENGINE)',
                style: TextStyle(
                  fontSize: 10,
                  fontWeight: FontWeight.w700,
                  color: AppColors.primaryGlow,
                  letterSpacing: 0.5,
                ),
              ),
            ),

          // 1c. Visible Audio Error State
          if (_audioErrorMessage != null)
            Container(
              width: double.infinity,
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              color: AppColors.danger.withValues(alpha: 0.2),
              child: Row(
                children: [
                  const Icon(
                    Icons.error_outline_rounded,
                    color: AppColors.danger,
                    size: 18,
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: Text(
                      _audioErrorMessage!,
                      style: AppTextStyles.caption.copyWith(
                        color: AppColors.danger,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                  TextButton(
                    onPressed: _retryAudio,
                    child: const Text(
                      'Retry Audio',
                      style: TextStyle(
                        color: AppColors.danger,
                        fontWeight: FontWeight.w700,
                        fontSize: 12,
                      ),
                    ),
                  ),
                ],
              ),
            ),

          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(
                horizontal: 20.0,
                vertical: 12.0,
              ),
              children: [
                // Top Header: Claimed Caller & Call Duration
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Claimed Caller',
                          style: AppTextStyles.caption.copyWith(
                            color: AppColors.textSecondary,
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(claimedName, style: AppTextStyles.subtitle),
                      ],
                    ),
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
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
                          child: Row(
                            mainAxisSize: MainAxisSize.min,
                            children: [
                              Container(
                                width: 8,
                                height: 8,
                                decoration: const BoxDecoration(
                                  shape: BoxShape.circle,
                                  color: AppColors.danger,
                                ),
                              ),
                              const SizedBox(width: 6),
                              Text(
                                durationStr,
                                style: const TextStyle(
                                  fontFamily: 'monospace',
                                  fontWeight: FontWeight.w700,
                                  fontSize: 12,
                                  color: AppColors.textPrimary,
                                ),
                              ),
                            ],
                          ),
                        ),
                        const SizedBox(height: 2),
                        Text(
                          _audioErrorMessage != null
                              ? 'Audio Error'
                              : (_isAudioReady
                                  ? 'Audio: ${TimeFormat.formatDuration(_playbackPosition)} / ${TimeFormat.formatDuration(_audioTotalDuration ?? const Duration(seconds: 17))}'
                                  : 'Initializing Audio...'),
                          style: TextStyle(
                            fontSize: 10,
                            color: _audioErrorMessage != null
                                ? AppColors.danger
                                : (_isAudioReady
                                    ? AppColors.success
                                    : AppColors.textSecondary),
                            fontWeight: FontWeight.w600,
                          ),
                        ),
                      ],
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // 2. High-Risk Emergency Alert Banner (when risk escalates)
                if (isDanger || isAmber)
                  Container(
                    margin: const EdgeInsets.only(bottom: 16),
                    padding: const EdgeInsets.all(12),
                    decoration: BoxDecoration(
                      color: (isDanger ? AppColors.danger : AppColors.warning)
                          .withValues(alpha: 0.15),
                      borderRadius: BorderRadius.circular(14),
                      border: Border.all(
                        color: isDanger ? AppColors.danger : AppColors.warning,
                        width: 1.5,
                      ),
                    ),
                    child: Row(
                      children: [
                        Icon(
                          isDanger
                              ? Icons.gpp_bad_rounded
                              : Icons.warning_amber_rounded,
                          color: isDanger
                              ? AppColors.danger
                              : AppColors.warning,
                          size: 24,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Text(
                            riskMonitor.latestAlertMessage,
                            style: TextStyle(
                              color: isDanger
                                  ? AppColors.danger
                                  : AppColors.warning,
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                              height: 1.3,
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),

                // 3. Central Real-Time Semi-Circle Risk Gauge
                GlassCard(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 16,
                    vertical: 20,
                  ),
                  child: Column(
                    children: [
                      RiskMeter(
                        riskIndex: riskMonitor.currentScore,
                        band: riskMonitor.currentBand,
                      ),
                      const SizedBox(height: 12),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          RiskBandBadge(band: riskMonitor.currentBand),
                          const SizedBox(width: 8),
                          StatusChip(
                            label: '${riskMonitor.lastLatencyMs}ms Latency',
                            tone: StatusTone.neutral,
                          ),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // 4. Evidence Quality Bar
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          const Text(
                            'Acoustic Evidence Quality',
                            style: AppTextStyles.caption,
                          ),
                          Text(
                            '${(riskMonitor.evidenceQuality * 100).round()}%',
                            style: const TextStyle(
                              fontFamily: 'monospace',
                              fontWeight: FontWeight.w600,
                              fontSize: 12,
                              color: AppColors.textPrimary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      EvidenceQualityBar(
                        level: riskMonitor.evidenceQuality > 0.7
                            ? EvidenceLevel.good
                            : (riskMonitor.evidenceQuality > 0.4
                                ? EvidenceLevel.limited
                                : EvidenceLevel.poor),
                        usableSpeechSec: riskMonitor.speechSeconds,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 16),

                // 5. Window Analysis Stats Row
                Row(
                  children: [
                    _buildStatTile(
                      label: 'Speech Analyzed',
                      value: '${riskMonitor.speechSeconds.toStringAsFixed(1)}s',
                      icon: Icons.graphic_eq_rounded,
                    ),
                    const SizedBox(width: 10),
                    _buildStatTile(
                      label: 'Windows Sliced',
                      value: '${riskMonitor.windowsAnalysed}',
                      icon: Icons.layers_rounded,
                    ),
                    const SizedBox(width: 10),
                    _buildStatTile(
                      label: 'Peak Risk',
                      value: '${riskMonitor.peakScore.round()}',
                      icon: Icons.shield_rounded,
                    ),
                  ],
                ),
                const SizedBox(height: 16),

                // 6. Real-Time Risk Progression Timeline Chart
                GlassCard(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const Row(
                        mainAxisAlignment: MainAxisAlignment.spaceBetween,
                        children: [
                          Text(
                            'Live Risk Progression',
                            style: AppTextStyles.caption,
                          ),
                          Text(
                            '3.5s window • 1.75s hop',
                            style: TextStyle(
                              fontSize: 10,
                              color: AppColors.textSecondary,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 12),
                      ScoreTimelineChart(
                        windowScores: riskMonitor.timelineScores.isEmpty
                            ? [riskMonitor.currentScore.round()]
                            : riskMonitor.timelineScores,
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // 7. Interactive Call Actions
                Padding(
                  padding: const EdgeInsets.only(bottom: 16.0),
                  child: Row(
                    children: [
                      // Independent Verification Button
                      Expanded(
                        flex: 3,
                        child: PrimaryButton(
                          label: 'Verify Caller',
                          icon: Icons.verified_user_rounded,
                          variant: ButtonVariant.secondary,
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
