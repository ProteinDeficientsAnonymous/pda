import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';

/// Fetches the EventPoll for an event (includes tallies, voters, and my votes).
final eventPollProvider = FutureProvider.family<EventPoll?, String>((
  ref,
  eventId,
) async {
  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get('/api/community/events/$eventId/poll/');
    return EventPoll.fromJson(response.data as Map<String, dynamic>);
  } on DioException catch (e) {
    if (e.response?.statusCode == 404) return null;
    rethrow;
  }
});

/// Submits or updates the current user's votes on an event poll.
Future<void> submitPollVote({
  required WidgetRef ref,
  required String eventId,
  required Map<String, String> votes,
}) async {
  final api = ref.read(apiClientProvider);
  await api.post(
    '/api/community/events/$eventId/poll/vote/',
    data: {'votes': votes},
  );
  ref.invalidate(eventPollProvider(eventId));
}

/// Finalizes an event poll by selecting a winning option.
Future<void> finalizeEventPoll({
  required WidgetRef ref,
  required String eventId,
  required String winningOptionId,
}) async {
  final api = ref.read(apiClientProvider);
  await api.post(
    '/api/community/events/$eventId/poll/finalize/',
    data: {'winning_option_id': winningOptionId},
  );
  ref.invalidate(eventPollProvider(eventId));
  ref.invalidate(eventDetailProvider(eventId));
  ref.invalidate(eventsProvider);
}

/// Adds a single datetime option to an existing poll.
Future<void> addPollOption({
  required WidgetRef ref,
  required String eventId,
  required DateTime datetime,
}) async {
  final api = ref.read(apiClientProvider);
  await api.post(
    '/api/community/events/$eventId/poll/options/',
    data: {'datetime': datetime.toUtc().toIso8601String()},
  );
  ref.invalidate(eventPollProvider(eventId));
}

/// Removes a single option from an existing poll.
Future<void> deletePollOption({
  required WidgetRef ref,
  required String eventId,
  required String optionId,
}) async {
  final api = ref.read(apiClientProvider);
  await api.delete('/api/community/events/$eventId/poll/options/$optionId/');
  ref.invalidate(eventPollProvider(eventId));
}

/// Deletes the event poll entirely.
Future<void> deleteEventPoll({
  required WidgetRef ref,
  required String eventId,
}) async {
  final api = ref.read(apiClientProvider);
  await api.delete('/api/community/events/$eventId/poll/');
  ref.invalidate(eventPollProvider(eventId));
  ref.invalidate(eventDetailProvider(eventId));
  ref.invalidate(eventsProvider);
}

/// Creates an event poll with a list of datetime options.
Future<void> createEventPoll({
  required WidgetRef ref,
  required String eventId,
  required List<DateTime> options,
}) async {
  final api = ref.read(apiClientProvider);
  await api.post(
    '/api/community/events/$eventId/poll/',
    data: {
      'options': options.map((dt) => dt.toUtc().toIso8601String()).toList(),
    },
  );
  ref.invalidate(eventPollProvider(eventId));
  ref.invalidate(eventDetailProvider(eventId));
  ref.invalidate(eventsProvider);
}
