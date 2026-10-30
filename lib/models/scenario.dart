import 'dart:convert';
import 'package:flutter/services.dart';

import '../utils/logger.dart';

/// Simulation Scenario Model for Voice Deepfake Demonstration
/// Aligns with assets/scenarios.json
class Scenario {
  final String id;
  final String title;
  final String claimedName;
  final String callerNumber;
  final String audioAsset;
  final int durationMs;
  final String description;
  final String expectedBand;
  final bool isDanger;

  const Scenario({
    required this.id,
    required this.title,
    required this.claimedName,
    required this.callerNumber,
    required this.audioAsset,
    required this.durationMs,
    required this.description,
    this.expectedBand = 'Simulation Scenario',
    this.isDanger = false,
  });

  factory Scenario.fromJson(Map<String, dynamic> json) {
    final id = json['id'] as String? ?? 'genuine_family';
    final isDanger = id == 'clone_ceo';
    String expectedBand = json['expectedBand'] as String? ?? '';
    if (expectedBand.isEmpty) {
      if (id == 'clone_ceo') {
        expectedBand = 'High Risk / Synthetic';
      } else if (id == 'genuine_family') {
        expectedBand = 'Low Risk / Genuine';
      } else if (id == 'noisy_call') {
        expectedBand = 'Medium / Adaptive Quality';
      } else if (id == 'short_insufficient') {
        expectedBand = 'Insufficient Evidence';
      } else {
        expectedBand = 'Simulation Scenario';
      }
    }

    return Scenario(
      id: id,
      title: json['title'] as String? ?? 'Simulation Scenario',
      claimedName: json['claimedName'] as String? ?? 'Unknown Caller',
      callerNumber: json['callerNumber'] as String? ?? 'Unknown',
      audioAsset: json['audioAsset'] as String? ?? 'assets/audio/calls/genuine_01.wav',
      durationMs: (json['durationMs'] as num?)?.toInt() ?? 17500,
      description: json['description'] as String? ?? '',
      expectedBand: expectedBand,
      isDanger: isDanger,
    );
  }

  Map<String, dynamic> toJson() => {
        'id': id,
        'title': title,
        'claimedName': claimedName,
        'callerNumber': callerNumber,
        'audioAsset': audioAsset,
        'durationMs': durationMs,
        'description': description,
        'expectedBand': expectedBand,
        'isDanger': isDanger,
      };

  /// The four standard demonstration scenarios matching assets/scenarios.json
  static const List<Scenario> defaultScenarios = [
    Scenario(
      id: 'clone_ceo',
      title: 'Cloned CEO Voice (Impersonation)',
      claimedName: 'Rakesh Sir',
      callerNumber: 'Unknown Caller',
      audioAsset: 'assets/audio/calls/clone_ceo_01.wav',
      durationMs: 21000,
      description:
          'High-urgency synthetic voice impersonating executive leadership requesting an urgent fund transfer.',
      expectedBand: 'High Risk / Synthetic',
      isDanger: true,
    ),
    Scenario(
      id: 'genuine_family',
      title: 'Genuine Family Call',
      claimedName: 'Priyanka',
      callerNumber: '+91 98xxxxxx01',
      audioAsset: 'assets/audio/calls/genuine_01.wav',
      durationMs: 17500,
      description:
          'Standard family check-in call with clean natural speech patterns and expected prosody.',
      expectedBand: 'Low Risk / Genuine',
      isDanger: false,
    ),
    Scenario(
      id: 'noisy_call',
      title: 'Noisy Background Scenario',
      claimedName: 'Delivery Agent',
      callerNumber: '+91 91xxxxxx42',
      audioAsset: 'assets/audio/calls/noisy_01.wav',
      durationMs: 17500,
      description:
          'Acoustically challenging audio demonstrating evidence quality assessment and adaptive thresholds.',
      expectedBand: 'Medium / Adaptive Quality',
      isDanger: false,
    ),
    Scenario(
      id: 'short_insufficient',
      title: 'Short or Degraded Speech Sample',
      claimedName: 'Bank Officer',
      callerNumber: '+91 80xxxxxx99',
      audioAsset: 'assets/audio/calls/short_insufficient_01.wav',
      durationMs: 17500,
      description:
          'Call with sparse speech testing system refusal to guess under inadequate acoustic evidence.',
      expectedBand: 'Insufficient Evidence',
      isDanger: false,
    ),
  ];

  static Scenario findById(String id) {
    return defaultScenarios.firstWhere(
      (s) => s.id == id,
      orElse: () => defaultScenarios.first,
    );
  }

  static String assetForScenarioId(String id) {
    return findById(id).audioAsset;
  }

  /// Loads scenarios dynamically from assets/scenarios.json with fallback to defaultScenarios
  static Future<List<Scenario>> loadAll() async {
    try {
      final jsonString = await rootBundle.loadString('assets/scenarios.json');
      final List<dynamic> list = jsonDecode(jsonString) as List<dynamic>;
      return list
          .map((item) => Scenario.fromJson(item as Map<String, dynamic>))
          .toList();
    } catch (e) {
      AppLogger.w('Failed to load assets/scenarios.json, using defaults: $e', 'Scenario');
      return defaultScenarios;
    }
  }
}
