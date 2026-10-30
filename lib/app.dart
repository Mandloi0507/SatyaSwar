import 'package:flutter/material.dart';

import 'config/app_config.dart';
import 'routing/app_router.dart';
import 'theme/app_theme.dart';

class SatyaSwarApp extends StatelessWidget {
  const SatyaSwarApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: AppConfig.appName,
      debugShowCheckedModeBanner: false,
      theme: AppTheme.darkTheme,
      routerConfig: appRouter,
    );
  }
}
