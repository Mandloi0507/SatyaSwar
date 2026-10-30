import 'package:flutter/material.dart';
import 'package:provider/provider.dart';

import 'config/app_config.dart';
import 'providers/auth_provider.dart';
import 'providers/call_history_provider.dart';
import 'providers/contacts_provider.dart';
import 'providers/risk_monitor_provider.dart';
import 'providers/settings_provider.dart';
import 'providers/verification_provider.dart';
import 'repositories/auth_repository.dart';
import 'repositories/call_history_repository.dart';
import 'repositories/contacts_repository.dart';
import 'repositories/settings_repository.dart';
import 'repositories/verification_repository.dart';
import 'routing/app_router.dart';
import 'theme/app_theme.dart';

class SatyaSwarApp extends StatefulWidget {
  final AuthRepository? authRepository;
  final SettingsRepository? settingsRepository;
  final ContactsRepository? contactsRepository;
  final CallHistoryRepository? callHistoryRepository;
  final VerificationRepository? verificationRepository;

  const SatyaSwarApp({
    super.key,
    this.authRepository,
    this.settingsRepository,
    this.contactsRepository,
    this.callHistoryRepository,
    this.verificationRepository,
  });

  @override
  State<SatyaSwarApp> createState() => _SatyaSwarAppState();
}

class _SatyaSwarAppState extends State<SatyaSwarApp> {
  late final AuthRepository _authRepo;
  late final SettingsRepository _settingsRepo;
  late final ContactsRepository _contactsRepo;
  late final CallHistoryRepository _historyRepo;
  late final VerificationRepository _verificationRepo;

  @override
  void initState() {
    super.initState();
    _authRepo = widget.authRepository ?? MockAuthRepository();
    _settingsRepo = widget.settingsRepository ?? SettingsRepositoryImpl();
    _contactsRepo = widget.contactsRepository ?? MockContactsRepository();
    _historyRepo = widget.callHistoryRepository ?? CallHistoryRepositoryImpl();
    _verificationRepo =
        widget.verificationRepository ?? MockVerificationRepository();
  }

  @override
  Widget build(BuildContext context) {
    return MultiProvider(
      providers: [
        ChangeNotifierProvider<AuthProvider>(
          create: (_) => AuthProvider(authRepository: _authRepo),
        ),
        ChangeNotifierProvider<SettingsProvider>(
          create: (_) => SettingsProvider(settingsRepository: _settingsRepo),
        ),
        ChangeNotifierProvider<ContactsProvider>(
          create: (_) => ContactsProvider(contactsRepository: _contactsRepo),
        ),
        ChangeNotifierProvider<CallHistoryProvider>(
          create: (_) => CallHistoryProvider(historyRepository: _historyRepo),
        ),
        ChangeNotifierProvider<VerificationProvider>(
          create: (_) =>
              VerificationProvider(repository: _verificationRepo),
        ),
        ChangeNotifierProvider<RiskMonitorProvider>(
          create: (_) => RiskMonitorProvider(),
        ),
      ],
      child: MaterialApp.router(
        title: AppConfig.appName,
        debugShowCheckedModeBanner: false,
        theme: AppTheme.darkTheme,
        routerConfig: appRouter,
      ),
    );
  }
}
