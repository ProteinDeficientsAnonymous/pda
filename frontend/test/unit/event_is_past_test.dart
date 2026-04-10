import 'package:flutter_test/flutter_test.dart';
import 'package:pda/models/event.dart';

Event _makeEvent({DateTime? start, DateTime? end}) => Event(
  id: 'test-id',
  title: 'Test Event',
  description: '',
  startDatetime: start ?? DateTime.now(),
  endDatetime: end,
  location: '',
);

void main() {
  group('Event.isPast', () {
    test('returns true when endDatetime is in the past', () {
      final event = _makeEvent(
        start: DateTime.now().subtract(const Duration(hours: 3)),
        end: DateTime.now().subtract(const Duration(hours: 1)),
      );
      expect(event.isPast, isTrue);
    });

    test('returns true when only startDatetime exists and is in the past', () {
      final event = _makeEvent(
        start: DateTime.now().subtract(const Duration(hours: 1)),
      );
      expect(event.isPast, isTrue);
    });

    test('returns false when endDatetime is in the future', () {
      final event = _makeEvent(
        start: DateTime.now().subtract(const Duration(hours: 1)),
        end: DateTime.now().add(const Duration(hours: 1)),
      );
      expect(event.isPast, isFalse);
    });

    test(
      'returns false when only startDatetime exists and is in the future',
      () {
        final event = _makeEvent(
          start: DateTime.now().add(const Duration(hours: 1)),
        );
        expect(event.isPast, isFalse);
      },
    );

    test(
      'returns false when event is currently happening (start past, end future)',
      () {
        final event = _makeEvent(
          start: DateTime.now().subtract(const Duration(hours: 1)),
          end: DateTime.now().add(const Duration(hours: 2)),
        );
        expect(event.isPast, isFalse);
      },
    );
  });
}
