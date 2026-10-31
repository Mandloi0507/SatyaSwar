import 'package:flutter/foundation.dart';
import '../models/trusted_contact.dart';
import '../repositories/contacts_repository.dart';

class ContactsProvider with ChangeNotifier {
  final ContactsRepository contactsRepository;

  List<TrustedContact> _contacts = [];
  bool _isLoading = false;
  String? _errorMessage;

  ContactsProvider({required this.contactsRepository}) {
    loadContacts();
  }

  List<TrustedContact> get contacts => List.unmodifiable(_contacts);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> loadContacts() async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      _contacts = await contactsRepository.getContacts();
      _isLoading = false;
      notifyListeners();
    } catch (e) {
      _errorMessage = e.toString();
      _isLoading = false;
      notifyListeners();
    }
  }

  Future<String> generateInviteCode(String issuerName) async {
    return contactsRepository.createInviteCode(issuerName: issuerName);
  }

  Future<bool> acceptInviteCode({
    required String code,
    required String contactName,
    String? alias,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    notifyListeners();

    try {
      final newContact = await contactsRepository.acceptInviteCode(
        code: code,
        contactName: contactName,
        alias: alias,
      );
      _contacts = [newContact, ..._contacts];
      _isLoading = false;
      notifyListeners();
      return true;
    } catch (e) {
      _errorMessage = e is FormatException ? e.message : e.toString();
      _isLoading = false;
      notifyListeners();
      return false;
    }
  }

  Future<void> removeContact(String contactId) async {
    _contacts.removeWhere((c) => c.id == contactId);
    notifyListeners();
    await contactsRepository.removeContact(contactId);
  }
}
