import 'dart:async';
import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';
import '../models/user_profile.dart';
import '../utils/logger.dart';

abstract class AuthRepository {
  Stream<UserProfile?> get authStateChanges;
  UserProfile? get currentUser;

  Future<UserProfile> signIn({
    required String email,
    required String password,
  });

  Future<UserProfile> register({
    required String email,
    required String password,
    required String displayName,
    String? phoneNumber,
  });

  Future<void> signOut();
  Future<void> restoreSession();
}

class MockAuthRepository implements AuthRepository {
  static const _userKey = 'satyaswar_mock_user';
  final _authController = StreamController<UserProfile?>.broadcast();
  UserProfile? _currentUser;

  MockAuthRepository() {
    restoreSession();
  }

  @override
  Stream<UserProfile?> get authStateChanges => _authController.stream;

  @override
  UserProfile? get currentUser => _currentUser;

  @override
  Future<void> restoreSession() async {
    try {
      final prefs = await SharedPreferences.getInstance();
      final userJson = prefs.getString(_userKey);
      if (userJson != null) {
        final Map<String, dynamic> data = jsonDecode(userJson);
        _currentUser = UserProfile.fromJson(data);
        _authController.add(_currentUser);
      } else {
        // Default guest user for quick demonstration
        _currentUser = UserProfile(
          uid: 'usr_demo_01',
          email: 'priyanka@satyaswar.io',
          displayName: 'Priyanka Mandloi',
          phoneNumber: '+91 98765 43210',
          createdAt: DateTime.now(),
        );
        _authController.add(_currentUser);
      }
    } catch (e) {
      AppLogger.w('Failed to restore session: $e', 'MockAuthRepository');
    }
  }

  @override
  Future<UserProfile> signIn({
    required String email,
    required String password,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 300));

    if (email.isEmpty || !email.contains('@')) {
      throw const FormatException('Please enter a valid email address');
    }
    if (password.length < 6) {
      throw const FormatException('Password must be at least 6 characters');
    }

    final user = UserProfile(
      uid: 'usr_${email.hashCode.abs()}',
      email: email,
      displayName: email.split('@').first,
      createdAt: DateTime.now(),
    );

    _currentUser = user;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userKey, jsonEncode(user.toJson()));
    _authController.add(_currentUser);

    return user;
  }

  @override
  Future<UserProfile> register({
    required String email,
    required String password,
    required String displayName,
    String? phoneNumber,
  }) async {
    await Future<void>.delayed(const Duration(milliseconds: 400));

    if (email.isEmpty || !email.contains('@')) {
      throw const FormatException('Please enter a valid email address');
    }
    if (password.length < 6) {
      throw const FormatException('Password must be at least 6 characters');
    }
    if (displayName.trim().isEmpty) {
      throw const FormatException('Please enter your full name');
    }

    final user = UserProfile(
      uid: 'usr_${email.hashCode.abs()}',
      email: email,
      displayName: displayName,
      phoneNumber: phoneNumber,
      createdAt: DateTime.now(),
    );

    _currentUser = user;
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_userKey, jsonEncode(user.toJson()));
    _authController.add(_currentUser);

    return user;
  }

  @override
  Future<void> signOut() async {
    _currentUser = null;
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_userKey);
    _authController.add(null);
  }
}
