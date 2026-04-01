import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/widgets/feedback_form.dart';

Widget _app(Widget child) => ProviderScope(
  child: MaterialApp(
    theme: ThemeData(splashFactory: NoSplash.splashFactory),
    home: Scaffold(body: child),
  ),
);

void main() {
  group('FeedbackForm', () {
    testWidgets('renders title and description fields', (tester) async {
      await tester.pumpWidget(
        _app(FeedbackForm(currentRoute: '/calendar', onClose: () {})),
      );
      await tester.pumpAndSettle();

      expect(find.byType(TextFormField), findsAtLeast(2));
      expect(find.textContaining('what happened'), findsOneWidget);
    });

    testWidgets('shows metadata section with current route', (tester) async {
      await tester.pumpWidget(
        _app(FeedbackForm(currentRoute: '/calendar', onClose: () {})),
      );
      await tester.pumpAndSettle();

      expect(find.textContaining('/calendar'), findsOneWidget);
    });

    testWidgets('calls onClose when cancel is tapped', (tester) async {
      var closed = false;
      await tester.pumpWidget(
        _app(
          FeedbackForm(currentRoute: '/calendar', onClose: () => closed = true),
        ),
      );
      await tester.pumpAndSettle();

      await tester.tap(find.textContaining('cancel'));
      expect(closed, isTrue);
    });
  });
}
