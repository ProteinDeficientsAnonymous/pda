import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/config/api_config.dart';
import 'package:pda/widgets/feedback_button.dart';

void main() {
  group('FeedbackButton', () {
    testWidgets('renders ? FAB', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(body: FeedbackButton(currentRoute: '/calendar')),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(find.byType(FloatingActionButton), findsOneWidget);
      expect(find.byIcon(Icons.help_outline), findsOneWidget);
    });

    testWidgets('opens feedback form on tap', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(body: FeedbackButton(currentRoute: '/calendar')),
          ),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();

      expect(find.textContaining('report a bug'), findsOneWidget);
    });

    testWidgets('closes feedback form on cancel', (tester) async {
      await tester.pumpWidget(
        ProviderScope(
          child: MaterialApp(
            home: Scaffold(body: FeedbackButton(currentRoute: '/calendar')),
          ),
        ),
      );
      await tester.pumpAndSettle();

      // Open
      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      expect(find.textContaining('report a bug'), findsOneWidget);

      // Close via cancel
      await tester.tap(find.textContaining('cancel'));
      await tester.pumpAndSettle();
      expect(find.textContaining('report a bug'), findsNothing);
    });
  });

  test('enableFeedback defaults to false', () {
    // Compile-time const — in test builds without --dart-define, should be false
    expect(enableFeedback, isFalse);
  });
}
