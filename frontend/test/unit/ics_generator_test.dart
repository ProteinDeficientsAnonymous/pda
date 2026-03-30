import 'package:flutter_test/flutter_test.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/ics_generator.dart';

void main() {
  group('generateEventIcs', () {
    test('generates valid ICS with all fields', () {
      final event = Event(
        id: 'abc-123',
        title: 'Vegan Potluck',
        description: 'Bring your best dish!',
        startDatetime: DateTime.utc(2026, 4, 15, 18, 0),
        endDatetime: DateTime.utc(2026, 4, 15, 21, 0),
        location: 'Central Park',
      );

      final ics = generateEventIcs(event);

      expect(ics, contains('BEGIN:VCALENDAR'));
      expect(ics, contains('END:VCALENDAR'));
      expect(ics, contains('BEGIN:VEVENT'));
      expect(ics, contains('END:VEVENT'));
      expect(ics, contains('UID:abc-123@pda'));
      expect(ics, contains('SUMMARY:Vegan Potluck'));
      expect(ics, contains('DTSTART:20260415T180000Z'));
      expect(ics, contains('DTEND:20260415T210000Z'));
      expect(ics, contains('DESCRIPTION:Bring your best dish!'));
      expect(ics, contains('LOCATION:Central Park'));
      expect(ics, contains('PRODID:-//PDA//PDA Calendar//EN'));
    });

    test('omits DTEND when endDatetime is null', () {
      final event = Event(
        id: 'abc-123',
        title: 'Open Hangout',
        description: '',
        startDatetime: DateTime.utc(2026, 4, 15, 18, 0),
        location: '',
      );

      final ics = generateEventIcs(event);

      expect(ics, contains('DTSTART:20260415T180000Z'));
      expect(ics, isNot(contains('DTEND')));
    });

    test('omits DESCRIPTION and LOCATION when empty', () {
      final event = Event(
        id: 'abc-123',
        title: 'Mystery Event',
        description: '',
        startDatetime: DateTime.utc(2026, 4, 15, 18, 0),
        location: '',
      );

      final ics = generateEventIcs(event);

      expect(ics, isNot(contains('DESCRIPTION')));
      expect(ics, isNot(contains('LOCATION')));
    });

    test('escapes special characters', () {
      final event = Event(
        id: 'abc-123',
        title: 'Fun, Games; and More',
        description: 'Line one\nLine two',
        startDatetime: DateTime.utc(2026, 4, 15, 18, 0),
        location: 'Room 1, Floor 2; Building A',
      );

      final ics = generateEventIcs(event);

      expect(ics, contains('Fun\\, Games\\; and More'));
      expect(ics, contains('Line one\\nLine two'));
      expect(ics, contains('Room 1\\, Floor 2\\; Building A'));
    });

    test('formats UTC dates correctly', () {
      final event = Event(
        id: 'abc-123',
        title: 'Test',
        description: '',
        startDatetime: DateTime.utc(2026, 1, 5, 9, 5, 3),
        location: '',
      );

      final ics = generateEventIcs(event);

      expect(ics, contains('DTSTART:20260105T090503Z'));
    });
  });
}
