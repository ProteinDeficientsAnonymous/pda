import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/event_poll_provider.dart';

/// Creates an EventPoll for an event with the given datetime options.
///
/// [options] must be ISO 8601 UTC strings (as returned by [EventFormResult.datetimePollOptions]).
Future<void> createDatetimePoll({
  required WidgetRef ref,
  required String eventId,
  @Deprecated('No longer used — polls are not linked to survey titles')
  String eventTitle = '',
  required List<String> options,
}) async {
  await createEventPoll(
    ref: ref,
    eventId: eventId,
    options: options.map(DateTime.parse).toList(),
  );
}
