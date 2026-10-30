import 'dart:async';
import 'dart:convert';
import 'dart:math';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/trusted_contact.dart';
import '../utils/logger.dart';

abstract class ContactsRepository {
  Future<List<TrustedContact>> getContacts();
  Future<String> createInviteCode({required String issuerName});
  Future<TrustedContact> acceptInviteCode({
    required String code,
    required String contactName,
    String? alias,
  });
  Future<void> removeContact(String contactId);
}

class MockContactsRepository implements ContactsRepository {
  static const _storageKey = 'satyaswar_contacts_list';
  final List<TrustedContact> _contacts = [];

  MockContactsRepository() {
    _initDefaultContacts();
  }

  Future<void> _initDefaultContacts() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final stored = prefs.getString(_storageKey);
      if (stored != null) {
        final List<dynamic> list = jsonDecode(stored);
        _contacts.clear();
        _contacts.addAll(
          list.map((e) => TrustedContact.fromJson(e as Map<String, dynamic>)),
        );
        return;
      }
    } catch (e) {
      AppLogger.w('Failed to load stored contacts: $e', 'ContactsRepository');
    }

    // Default realistic contacts
    if (_contacts.isEmpty) {
      _contacts.addAll([
        TrustedContact(
          id: 'cnt_01',
          name: 'Rakesh Sir',
          phoneNumber: '+91 98200 11223',
          alias: 'CEO / Executive',
          isVerified: true,
          createdAt: DateTime.now().subtract(const Duration(days: 14)),
        ),
        TrustedContact(
          id: 'cnt_02',
          name: 'Priyanka Mandloi',
          phoneNumber: '+91 94250 88990',
          alias: 'Family',
          isVerified: true,
          createdAt: DateTime.now().subtract(const Duration(days: 30)),
        ),
        TrustedContact(
          id: 'cnt_03',
          name: 'Anand Kumar',
          phoneNumber: '+91 98111 22334',
          alias: 'Finance Director',
          isVerified: true,
          createdAt: DateTime.now().subtract(const Duration(days: 7)),
        ),
      ]);
      _save();
    }
  }

  Future<void> _save() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final jsonList = _contacts.map((c) => c.toJson()).toList();
      await prefs.setString(_storageKey, jsonEncode(jsonList));
    } catch (e) {
      AppLogger.w('Failed to save contacts: $e', 'ContactsRepository');
    }
  }

  @override
  Future<List<TrustedContact>> getContacts() async {
    if (_contacts.isEmpty) {
      await _initDefaultContacts();
    }
    return List.unmodifiable(_contacts);
  }

  @override
  Future<String> createInviteCode({required String issuerName}) async {
    await Future<void>.delayed(const Duration(milliseconds: 200));
    final random = Random();
    final num = 1000 + random.nextInt(9000);
    return 'SW-$num';
  }

  @override
  Future<TrustedContact> acceptInviteCode({
    required String code,
    required String contactName,
    String? alias,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 350));

    if (code.trim().isEmpty) {
      throw const FormatException('Invite code cannot be empty');
    }
    if (contactName.trim().isEmpty) {
      throw const FormatException('Contact name is required');
    }

    final newContact = TrustedContact(
      id: 'cnt_${DateTime.now().millisecondsSinceEpoch}',
      name: contactName.trim(),
      phoneNumber: '+91 98${Random().nextInt(90000000) + 10000000}',
      alias: alias?.trim().isNotEmpty == true ? alias!.trim() : 'Colleague',
      inviteCode: code.toUpperCase().trim(),
      isVerified: true,
      createdAt: DateTime.now(),
    );

    _contacts.insert(0, newContact);
    await _save();
    return newContact;
  }

  @override
  Future<void> removeContact(String contactId) async {
    _contacts.removeWhere((c) => c.id == contactId);
    await _save();
  }
}
