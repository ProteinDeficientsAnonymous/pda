import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/day_view.dart';
import 'package:pda/screens/calendar/week_view.dart';

void main() {
  final testEvent = Event(
    id: 'test-1',
    title: 'Community Potluck',
    description: 'Bring vegan food',
    startDatetime: DateTime(2026, 3, 25, 18, 0),
    endDatetime: DateTime(2026, 3, 25, 21, 0),
    location: 'Park',
  );

  group('WeekView accessibility', () {
    Widget buildWeekView({List<Event> events = const []}) {
      return MaterialApp(
        home: Scaffold(
          body: WeekView(
            events: events,
            selectedDate: DateTime(2026, 3, 25),
            onDateChanged: (_) {},
          ),
        ),
      );
    }

    testWidgets('week header date picker trigger is accessible', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(buildWeekView());

      final semantics = find.byWidgetPredicate(
        (w) => w is Semantics && w.properties.label == 'Pick week',
      );
      expect(semantics, findsOneWidget);
      handle.dispose();
    });

    testWidgets('event chips have semantic labels with event title', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(buildWeekView(events: [testEvent]));

      final eventSemantics = find.byWidgetPredicate(
        (w) =>
            w is Semantics &&
            w.properties.label == 'Community Potluck' &&
            w.properties.button == true,
      );
      expect(eventSemantics, findsOneWidget);
      handle.dispose();
    });
  });

  group('DayView accessibility', () {
    Widget buildDayView({List<Event> events = const []}) {
      return MaterialApp(
        home: Scaffold(
          body: DayView(
            events: events,
            selectedDate: DateTime(2026, 3, 25),
            onDateChanged: (_) {},
          ),
        ),
      );
    }

    testWidgets('day header date picker trigger is accessible', (tester) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(buildDayView());

      final semantics = find.byWidgetPredicate(
        (w) => w is Semantics && w.properties.label == 'Pick date',
      );
      expect(semantics, findsOneWidget);
      handle.dispose();
    });

    testWidgets('event cards have semantic labels with event title', (
      tester,
    ) async {
      final handle = tester.ensureSemantics();
      await tester.pumpWidget(buildDayView(events: [testEvent]));

      final eventSemantics = find.byWidgetPredicate(
        (w) =>
            w is Semantics &&
            w.properties.label == 'Community Potluck' &&
            w.properties.button == true,
      );
      expect(eventSemantics, findsOneWidget);
      handle.dispose();
    });
  });
}
