import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_form_result.dart';
import 'package:pda/utils/create_datetime_poll.dart';

/// Submits a new event (or draft) via the API, uploads the photo if provided,
/// creates a datetime poll if options were specified, then invalidates
/// the events cache. Returns the ID of the newly created event.
Future<String> submitNewEvent(WidgetRef ref, EventFormResult result) async {
  final api = ref.read(apiClientProvider);
  final body = {...result.data, 'status': result.status};
  final response = await api.post('/api/community/events/', data: body);
  final eventId = (response.data as Map<String, dynamic>)['id'] as String;
  if (result.photo != null) {
    await uploadEventPhoto(ref, eventId, result.photo!);
  }
  if (result.datetimePollOptions.isNotEmpty) {
    await createDatetimePoll(
      ref: ref,
      eventId: eventId,
      eventTitle: result.data['title'] as String,
      options: result.datetimePollOptions,
    );
  }
  ref.invalidate(eventsProvider);
  ref.invalidate(draftEventsProvider);
  return eventId;
}

/// Publishes a saved draft by transitioning it to active status.
/// Invalidates all relevant providers.
Future<void> publishDraft(WidgetRef ref, String eventId) async {
  final api = ref.read(apiClientProvider);
  await api.patch(
    '/api/community/events/$eventId/',
    data: {'status': 'active'},
  );
  ref.invalidate(eventsProvider);
  ref.invalidate(draftEventsProvider);
  ref.invalidate(eventDetailProvider(eventId));
}
