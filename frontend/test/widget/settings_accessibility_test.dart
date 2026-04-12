import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/screens/settings_dialogs.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  group('SettingsAccessibilitySection', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    testWidgets('renders theme mode selector with system selected by default', (
      tester,
    ) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: Scaffold(body: SettingsAccessibilitySection()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.text('theme'), findsOneWidget);
      expect(find.text('system'), findsOneWidget);
      expect(find.text('light'), findsOneWidget);
      expect(find.text('dark'), findsOneWidget);
    });

    testWidgets('tapping dark segment updates theme mode', (tester) async {
      await tester.pumpWidget(
        const ProviderScope(
          child: MaterialApp(
            home: Scaffold(body: SettingsAccessibilitySection()),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.text('dark'));
      await tester.pumpAndSettle();

      final sp = await SharedPreferences.getInstance();
      expect(sp.getString('pda_theme_mode'), 'dark');
    });
  });
}
