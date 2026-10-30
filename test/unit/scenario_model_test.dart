import 'package:flutter_test/flutter_test.dart';
import 'package:satyaswar_app/models/scenario.dart';

void main() {
  group('Scenario Model Tests', () {
    test('defaultScenarios contains exactly 4 standard scenarios', () {
      expect(Scenario.defaultScenarios.length, equals(4));
    });

    test('each default scenario has a unique ID', () {
      final ids = Scenario.defaultScenarios.map((s) => s.id).toSet();
      expect(ids.length, equals(4));
      expect(ids, containsAll(['clone_ceo', 'genuine_family', 'noisy_call', 'short_insufficient']));
    });

    test('clone_ceo scenario maps to correct audio asset', () {
      final s = Scenario.findById('clone_ceo');
      expect(s.id, equals('clone_ceo'));
      expect(s.audioAsset, equals('assets/audio/calls/clone_ceo_01.wav'));
      expect(s.isDanger, isTrue);
      expect(s.expectedBand, equals('High Risk / Synthetic'));
    });

    test('genuine_family scenario maps to correct audio asset', () {
      final s = Scenario.findById('genuine_family');
      expect(s.id, equals('genuine_family'));
      expect(s.audioAsset, equals('assets/audio/calls/genuine_01.wav'));
      expect(s.isDanger, isFalse);
      expect(s.expectedBand, equals('Low Risk / Genuine'));
    });

    test('noisy_call scenario maps to correct audio asset', () {
      final s = Scenario.findById('noisy_call');
      expect(s.id, equals('noisy_call'));
      expect(s.audioAsset, equals('assets/audio/calls/noisy_01.wav'));
      expect(s.isDanger, isFalse);
      expect(s.expectedBand, equals('Medium / Adaptive Quality'));
    });

    test('short_insufficient scenario maps to correct audio asset', () {
      final s = Scenario.findById('short_insufficient');
      expect(s.id, equals('short_insufficient'));
      expect(s.audioAsset, equals('assets/audio/calls/short_insufficient_01.wav'));
      expect(s.isDanger, isFalse);
      expect(s.expectedBand, equals('Insufficient Evidence'));
    });

    test('assetForScenarioId returns correct path for all scenarios', () {
      expect(Scenario.assetForScenarioId('clone_ceo'), equals('assets/audio/calls/clone_ceo_01.wav'));
      expect(Scenario.assetForScenarioId('genuine_family'), equals('assets/audio/calls/genuine_01.wav'));
      expect(Scenario.assetForScenarioId('noisy_call'), equals('assets/audio/calls/noisy_01.wav'));
      expect(Scenario.assetForScenarioId('short_insufficient'), equals('assets/audio/calls/short_insufficient_01.wav'));
    });

    test('findById falls back to first default when ID is unknown', () {
      final s = Scenario.findById('nonexistent_scenario');
      expect(s.id, equals('clone_ceo'));
    });

    test('fromJson parses complete JSON correctly', () {
      final json = {
        'id': 'clone_ceo',
        'title': 'Cloned CEO Voice',
        'claimedName': 'Rakesh Sir',
        'callerNumber': '+91 00000000',
        'audioAsset': 'assets/audio/calls/clone_ceo_01.wav',
        'durationMs': 21000,
        'description': 'Test description',
        'expectedBand': 'High Risk / Synthetic',
      };

      final s = Scenario.fromJson(json);
      expect(s.id, equals('clone_ceo'));
      expect(s.title, equals('Cloned CEO Voice'));
      expect(s.audioAsset, equals('assets/audio/calls/clone_ceo_01.wav'));
      expect(s.durationMs, equals(21000));
      expect(s.isDanger, isTrue);
    });

    test('fromJson assigns correct defaults for missing fields', () {
      final s = Scenario.fromJson(<String, dynamic>{});
      expect(s.id, equals('genuine_family'));
      expect(s.title, equals('Simulation Scenario'));
      expect(s.audioAsset, equals('assets/audio/calls/genuine_01.wav'));
      expect(s.durationMs, equals(17500));
      expect(s.isDanger, isFalse);
    });

    test('fromJson infers expectedBand when not provided', () {
      final ceo = Scenario.fromJson({'id': 'clone_ceo'});
      expect(ceo.expectedBand, equals('High Risk / Synthetic'));

      final family = Scenario.fromJson({'id': 'genuine_family'});
      expect(family.expectedBand, equals('Low Risk / Genuine'));

      final noisy = Scenario.fromJson({'id': 'noisy_call'});
      expect(noisy.expectedBand, equals('Medium / Adaptive Quality'));

      final short = Scenario.fromJson({'id': 'short_insufficient'});
      expect(short.expectedBand, equals('Insufficient Evidence'));
    });

    test('toJson round-trips back through fromJson', () {
      for (final original in Scenario.defaultScenarios) {
        final json = original.toJson();
        final restored = Scenario.fromJson(json);
        expect(restored.id, equals(original.id));
        expect(restored.audioAsset, equals(original.audioAsset));
        expect(restored.durationMs, equals(original.durationMs));
        expect(restored.isDanger, equals(original.isDanger));
      }
    });

    test('all default scenarios have non-empty audioAsset paths', () {
      for (final s in Scenario.defaultScenarios) {
        expect(s.audioAsset.isNotEmpty, isTrue, reason: '${s.id} has empty audioAsset');
        expect(s.audioAsset.startsWith('assets/audio/calls/'), isTrue,
            reason: '${s.id} audioAsset does not start with expected prefix');
        expect(s.audioAsset.endsWith('.wav'), isTrue,
            reason: '${s.id} audioAsset does not end with .wav');
      }
    });

    test('all default scenarios have positive durationMs', () {
      for (final s in Scenario.defaultScenarios) {
        expect(s.durationMs, greaterThan(0), reason: '${s.id} has non-positive durationMs');
      }
    });
  });
}
