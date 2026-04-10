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

    testWidgets('does not show metadata chips to user', (tester) async {
      await tester.pumpWidget(
        _app(FeedbackForm(currentRoute: '/donate', onClose: () {})),
      );
      await tester.pumpAndSettle();

      expect(find.byType(Chip), findsNothing);
      expect(find.textContaining('/donate'), findsNothing);
    });

    testWidgets('title field has maxLength 200', (tester) async {
      await tester.pumpWidget(
        _app(FeedbackForm(currentRoute: '/calendar', onClose: () {})),
      );
      await tester.pumpAndSettle();

      final titleField = tester
          .widgetList<TextField>(find.byType(TextField))
          .first;
      expect(titleField.maxLength, 200);
    });

    testWidgets('description field has maxLength 2000', (tester) async {
      await tester.pumpWidget(
        _app(FeedbackForm(currentRoute: '/calendar', onClose: () {})),
      );
      await tester.pumpAndSettle();

      final descField = tester
          .widgetList<TextField>(find.byType(TextField))
          .elementAt(1);
      expect(descField.maxLength, 2000);
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
