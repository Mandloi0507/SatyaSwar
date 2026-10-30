import 'package:flutter/foundation.dart';
import '../models/call_history_record.dart';
import '../repositories/call_history_repository.dart';

class CallHistoryProvider with ChangeNotifier {
  final CallHistoryRepository historyRepository;

  List<CallHistoryRecord> _records = [];
  bool _isLoading = false;

  CallHistoryProvider({required this.historyRepository}) {
    loadHistory();
  }

  List<CallHistoryRecord> get records => List.unmodifiable(_records);
  bool get isLoading => _isLoading;

  Future<void> loadHistory() async {
    _isLoading = true;
    notifyListeners();

    _records = await historyRepository.getCallHistory();
    _isLoading = false;
    notifyListeners();
  }

  Future<void> addRecord(CallHistoryRecord record) async {
    await historyRepository.saveCallRecord(record);
    _records = [record, ..._records];
    notifyListeners();
  }

  Future<CallHistoryRecord?> getDetail(String id) async {
    return historyRepository.getCallDetail(id);
  }

  Future<void> clearHistory() async {
    await historyRepository.clearHistory();
    _records.clear();
    notifyListeners();
  }
}
