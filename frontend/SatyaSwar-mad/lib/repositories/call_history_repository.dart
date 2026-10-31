import 'dart:async';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/call_history_record.dart';
import '../models/risk_band.dart';
import '../utils/logger.dart';

abstract class CallHistoryRepository {
  Future<List<CallHistoryRecord>> getCallHistory();
  Future<CallHistoryRecord?> getCallDetail(String id);
  Future<void> saveCallRecord(CallHistoryRecord record);
  Future<void> clearHistory();
}

class CallHistoryRepositoryImpl implements CallHistoryRepository {
  static const _storageKey = 'satyaswar_call_history';
  final List<CallHistoryRecord> _records = [];

  CallHistoryRepositoryImpl() {
    _loadHistory();
  }

  Future<void> _loadHistory() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(_storageKey);
      if (stored != null) {
        final List<dynamic> list = jsonDecode(stored);
        _records.clear();
        _records.addAll(
          list.map((e) => CallHistoryRecord.fromJson(e as Map<String, dynamic>)),
        );
        return;
      }
    } catch (e) {
      AppLogger.w('Failed to load call history: $e', 'HistoryRepository');
    }

    // Default realistic records for demonstration
    if (_records.isEmpty) {
      _records.addAll([
        CallHistoryRecord(
          id: 'call_demo_01',
          callerName: 'Rakesh Sir (CEO)',
          callerNumber: '+91 98200 11223',
          timestamp: DateTime.now().subtract(const Duration(minutes: 25)),
          durationSeconds: 21,
          peakRiskScore: 88,
          peakRiskBand: RiskBand.high,
          evidenceQuality: 0.94,
          verificationStatus: 'denied',
          finalOutcome: 'High Risk / Synthetic Impersonation Blocked',
          timelineScores: [18, 22, 52, 68, 84, 88, 86, 85, 87, 88, 85],
        ),
        CallHistoryRecord(
          id: 'call_demo_02',
          callerName: 'Priyanka (Family)',
          callerNumber: '+91 94250 88990',
          timestamp: DateTime.now().subtract(const Duration(hours: 3)),
          durationSeconds: 18,
          peakRiskScore: 16,
          peakRiskBand: RiskBand.low,
          evidenceQuality: 0.96,
          verificationStatus: 'confirmed',
          finalOutcome: 'No synthetic indicators detected',
          timelineScores: [10, 13, 16, 12, 10, 13, 14, 11, 15],
        ),
        CallHistoryRecord(
          id: 'call_demo_03',
          callerName: 'Bank Representative',
          callerNumber: '+91 80000 99999',
          timestamp: DateTime.now().subtract(const Duration(days: 1)),
          durationSeconds: 14,
          peakRiskScore: 0,
          peakRiskBand: RiskBand.unknown,
          evidenceQuality: 0.22,
          verificationStatus: 'unverified',
          finalOutcome: 'Insufficient speech evidence',
          timelineScores: [0, 0, 0, 0, 0],
        ),
      ]);
      _persist();
    }
  }

  Future<void> _persist() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonList = _records.map((r) => r.toJson()).toList();
      await prefs.setString(_storageKey, jsonEncode(jsonList));
    } catch (e) {
      AppLogger.w('Failed to save call history: $e', 'HistoryRepository');
    }
  }

  @override
  Future<List<CallHistoryRecord>> getCallHistory() async {
    if (_records.isEmpty) {
      await _loadHistory();
    }
    return List.unmodifiable(_records);
  }

  @override
  Future<CallHistoryRecord?> getCallDetail(String id) async {
    if (_records.isEmpty) {
      await _loadHistory();
    }
    try {
      return _records.firstWhere((r) => r.id == id);
    } catch (_) {
      return null;
    }
  }

  @override
  Future<void> saveCallRecord(CallHistoryRecord record) async {
    _records.insert(0, record);
    await _persist();
  }

  @override
  Future<void> clearHistory() async {
    _records.clear();
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_storageKey);
  }
}
