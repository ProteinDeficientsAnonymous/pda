import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/list_view.dart';

Widget _buildSubject({required List<Event> events}) {
  final router = GoRouter(
    routes: [
      GoRoute(
        path: '/',
        builder: (_, __) => Scaffold(body: EventListView(events: events)),
      ),
      GoRoute(
        path: '/events/:id',
        builder: (_, __) => const Scaffold(body: Text('event detail')),
      ),
    ],
  );
  return MaterialApp.router(routerConfig: router);
}

final _upcoming = Event(
  id: 'evt-1',
  title: 'Future Feast',
  description: 'A great event',
  startDatetime: DateTime.now().add(const Duration(days: 7)),
  endDatetime: DateTime.now().add(const Duration(days: 7, hours: 2)),
  location: 'The Park',
  eventType: 'community',
);

final _past = Event(
  id: 'evt-2',
  title: 'Old Gathering',
  description: 'A past event',
  startDatetime: DateTime.now().subtract(const Duration(days: 30)),
  endDatetime: DateTime.now()
      .subtract(const Duration(days: 30))
      .add(const Duration(hours: 2)),
  location: 'Community Centre',
  eventType: 'official',
);

final _official = Event(
  id: 'evt-3',
  title: 'Official Meetup',
  description: '',
  location: '',
  startDatetime: DateTime.now().add(const Duration(days: 3)),
  eventType: 'official',
);

void main() {
  testWidgets('renders all upcoming events by default', (tester) async {
    await tester.pumpWidget(_buildSubject(events: [_upcoming, _past]));
    await tester.pumpAndSettle();

    expect(find.text('Future Feast'), findsOneWidget);
    expect(find.text('Old Gathering'), findsNothing);
  });

  testWidgets('switching to past shows past events', (tester) async {
    await tester.pumpWidget(_buildSubject(events: [_upcoming, _past]));
    await tester.pumpAndSettle();

    await tester.tap(find.text('past'));
    await tester.pumpAndSettle();

    expect(find.text('Old Gathering'), findsOneWidget);
    expect(find.text('Future Feast'), findsNothing);
  });

  testWidgets('search by title filters results', (tester) async {
    await tester.pumpWidget(_buildSubject(events: [_upcoming, _official]));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'official');
    await tester.pumpAndSettle();

    expect(find.text('Official Meetup'), findsOneWidget);
    expect(find.text('Future Feast'), findsNothing);
  });

  testWidgets('clear search button resets query', (tester) async {
    await tester.pumpWidget(_buildSubject(events: [_upcoming, _official]));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'feast');
    await tester.pumpAndSettle();
    expect(find.text('Official Meetup'), findsNothing);

    await tester.tap(find.byTooltip('clear search'));
    await tester.pumpAndSettle();

    expect(find.text('Future Feast'), findsOneWidget);
    expect(find.text('Official Meetup'), findsOneWidget);
  });

  // Type filter tests moved to calendar_type_filter_test.dart (filter now
  // lives in CalendarScreen, shared across all views).

  testWidgets('empty state shown when no upcoming events', (tester) async {
    await tester.pumpWidget(_buildSubject(events: [_past]));
    await tester.pumpAndSettle();

    expect(find.text('nothing upcoming 🌿'), findsOneWidget);
  });

  testWidgets('empty state shown when search has no matches', (tester) async {
    await tester.pumpWidget(_buildSubject(events: [_upcoming]));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField), 'zzznomatch');
    await tester.pumpAndSettle();

    expect(find.textContaining('no matches for'), findsOneWidget);
  });

  testWidgets('tapping a row navigates to event detail', (tester) async {
    await tester.pumpWidget(_buildSubject(events: [_upcoming]));
    await tester.pumpAndSettle();

    await tester.tap(find.text('Future Feast'));
    await tester.pumpAndSettle();

    expect(find.text('event detail'), findsOneWidget);
  });

  testWidgets('sort direction toggle changes order', (tester) async {
    tester.view.physicalSize = const Size(1200, 900);
    tester.view.devicePixelRatio = 1.0;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);

    final earlier = Event(
      id: 'evt-a',
      title: 'Earlier Event',
      description: '',
      location: '',
      startDatetime: DateTime.now().add(const Duration(days: 1)),
    );
    final later = Event(
      id: 'evt-b',
      title: 'Later Event',
      description: '',
      location: '',
      startDatetime: DateTime.now().add(const Duration(days: 10)),
    );

    await tester.pumpWidget(_buildSubject(events: [later, earlier]));
    await tester.pumpAndSettle();

    // Default: ascending (oldest first) — Earlier Event renders above Later Event
    final earlierPos = tester.getTopLeft(find.text('Earlier Event'));
    final laterPos = tester.getTopLeft(find.text('Later Event'));
    expect(earlierPos.dy, lessThan(laterPos.dy));

    // Tap sort button to flip to descending (newest first)
    await tester.tap(find.byTooltip('sort newest first'));
    await tester.pumpAndSettle();

    final earlierPosDesc = tester.getTopLeft(find.text('Earlier Event'));
    final laterPosDesc = tester.getTopLeft(find.text('Later Event'));
    expect(laterPosDesc.dy, lessThan(earlierPosDesc.dy));
  });
}
