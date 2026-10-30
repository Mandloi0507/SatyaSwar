import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/call/active_call_screen.dart';
import '../screens/call/incoming_call_screen.dart';
import '../screens/call/scenario_picker_screen.dart';
import '../screens/contacts/add_contact_screen.dart';
import '../screens/contacts/contacts_screen.dart';
import '../screens/contacts/scan_invite_screen.dart';
import '../screens/history/history_detail_screen.dart';
import '../screens/history/history_screen.dart';
import '../screens/home/home_screen.dart';
import '../screens/main_shell_screen.dart';
import '../screens/settings/settings_screen.dart';
import '../screens/splash/splash_screen.dart';
import '../screens/style_guide_screen.dart';
import '../screens/verification/outcome_screen.dart';
import '../screens/verification/responder_screen.dart';

final GlobalKey<NavigatorState> _rootNavigatorKey = GlobalKey<NavigatorState>(
  debugLabel: 'root',
);

final GoRouter appRouter = GoRouter(
  navigatorKey: _rootNavigatorKey,
  initialLocation: '/',
  routes: [
    // 1. Splash Screen
    GoRoute(path: '/', builder: (context, state) => const SplashScreen()),

    // 2. Authentication Flow
    GoRoute(path: '/login', builder: (context, state) => const LoginScreen()),
    GoRoute(
      path: '/register',
      builder: (context, state) => const RegisterScreen(),
    ),

    // 3. Main Application Stateful Shell (Bottom Navigation)
    StatefulShellRoute.indexedStack(
      builder: (context, state, navigationShell) {
        return MainShellScreen(navigationShell: navigationShell);
      },
      branches: [
        // Tab 0: Home Dashboard
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/home',
              builder: (context, state) => const HomeScreen(),
            ),
          ],
        ),

        // Tab 1: Trusted Contacts
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/contacts',
              builder: (context, state) => const ContactsScreen(),
            ),
          ],
        ),

        // Tab 2: Scores-Only History
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/history',
              builder: (context, state) => const HistoryScreen(),
            ),
          ],
        ),

        // Tab 3: Settings
        StatefulShellBranch(
          routes: [
            GoRoute(
              path: '/settings',
              builder: (context, state) => const SettingsScreen(),
            ),
          ],
        ),
      ],
    ),

    // 4. Contacts Sub-Routes
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/contacts/add',
      builder: (context, state) => const AddContactScreen(),
    ),
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/contacts/scan',
      builder: (context, state) => const ScanInviteScreen(),
    ),

    // 5. Simulated Call Flow (Full screen, hides bottom navigation)
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/call/scenarios',
      builder: (context, state) => const ScenarioPickerScreen(),
    ),
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/call/incoming',
      builder: (context, state) {
        final data = state.extra as Map<String, dynamic>?;
        return IncomingCallScreen(scenarioData: data);
      },
    ),
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/call/active',
      builder: (context, state) {
        final data = state.extra as Map<String, dynamic>?;
        return ActiveCallScreen(scenarioData: data);
      },
    ),
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/call/outcome',
      builder: (context, state) {
        final data = state.extra as Map<String, dynamic>?;
        return OutcomeScreen(outcomeData: data);
      },
    ),

    // 6. History Details
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/history/:id',
      builder: (context, state) {
        final id = state.pathParameters['id'] ?? 'call_0';
        final data = state.extra as Map<String, dynamic>?;
        return HistoryDetailScreen(callId: id, itemData: data);
      },
    ),

    // 7. Responder & Verification Gate
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/responder',
      builder: (context, state) => const ResponderScreen(),
    ),

    // 8. Style Guide
    GoRoute(
      parentNavigatorKey: _rootNavigatorKey,
      path: '/style-guide',
      builder: (context, state) => const StyleGuideScreen(),
    ),
  ],
);
