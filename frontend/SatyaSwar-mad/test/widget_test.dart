import 'package:flutter_test/flutter_test.dart';
import 'package:satyaswar_app/app.dart';

void main() {
  testWidgets('SatyaSwarApp initial smoke test', (WidgetTester tester) async {
    await tester.pumpWidget(const SatyaSwarApp());
    // Advance past splash timer (1500ms)
    await tester.pump(const Duration(seconds: 2));
    await tester.pumpAndSettle();

    expect(find.byType(SatyaSwarApp), findsOneWidget);
  });
}
