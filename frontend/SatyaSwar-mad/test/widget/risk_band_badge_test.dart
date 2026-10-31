import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:satyaswar_app/models/risk_band.dart';
import 'package:satyaswar_app/theme/app_colors.dart';
import 'package:satyaswar_app/widgets/common/risk_band_badge.dart';

void main() {
  group('RiskBandBadge Widget Tests', () {
    testWidgets('renders LOW RISK badge with correct label and green color', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: RiskBandBadge(band: RiskBand.low)),
        ),
      );

      expect(find.text('LOW RISK'), findsOneWidget);
      expect(find.byIcon(Icons.shield_rounded), findsOneWidget);

      final textWidget = tester.widget<Text>(find.text('LOW RISK'));
      expect(textWidget.style?.color, equals(AppColors.riskLow));
    });

    testWidgets(
      'renders MEDIUM RISK badge with correct label and amber color',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(body: RiskBandBadge(band: RiskBand.medium)),
          ),
        );

        expect(find.text('MEDIUM RISK'), findsOneWidget);
        expect(find.byIcon(Icons.gpp_maybe_rounded), findsOneWidget);

        final textWidget = tester.widget<Text>(find.text('MEDIUM RISK'));
        expect(textWidget.style?.color, equals(AppColors.riskMedium));
      },
    );

    testWidgets('renders HIGH RISK badge with correct label and red color', (
      WidgetTester tester,
    ) async {
      await tester.pumpWidget(
        const MaterialApp(
          home: Scaffold(body: RiskBandBadge(band: RiskBand.high)),
        ),
      );

      expect(find.text('HIGH RISK'), findsOneWidget);
      expect(find.byIcon(Icons.gpp_bad_rounded), findsOneWidget);

      final textWidget = tester.widget<Text>(find.text('HIGH RISK'));
      expect(textWidget.style?.color, equals(AppColors.riskHigh));
    });

    testWidgets(
      'renders INSUFFICIENT badge with correct label and neutral color',
      (WidgetTester tester) async {
        await tester.pumpWidget(
          const MaterialApp(
            home: Scaffold(body: RiskBandBadge(band: RiskBand.unknown)),
          ),
        );

        expect(find.text('INSUFFICIENT'), findsOneWidget);
        expect(find.byIcon(Icons.help_outline_rounded), findsOneWidget);

        final textWidget = tester.widget<Text>(find.text('INSUFFICIENT'));
        expect(textWidget.style?.color, equals(AppColors.riskUnknown));
      },
    );
  });
}
