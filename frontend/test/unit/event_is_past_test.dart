import 'package:flutter_test/flutter_test.dart';
import 'package:pda/models/event.dart';

Event _makeEvent({required bool isPast}) => Event(
  id: 'test-id',
  title: 'Test Event',
  description: '',
  startDatetime: DateTime.now(),
  location: '',
  isPast: isPast,
);

void main() {
  group('Event.isPast', () {
    test('is true when server marks event as past', () {
      final event = _makeEvent(isPast: true);
      expect(event.isPast, isTrue);
    });

    test('is false when server marks event as not past', () {
      final event = _makeEvent(isPast: false);
      expect(event.isPast, isFalse);
    });

    test('defaults to false', () {
      final event = Event(
        id: 'test-id',
        title: 'Test Event',
        description: '',
        startDatetime: DateTime.now(),
        location: '',
      );
      expect(event.isPast, isFalse);
    });
  });
}
