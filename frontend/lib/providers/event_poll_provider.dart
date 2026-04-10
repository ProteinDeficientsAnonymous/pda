import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';

final _log = Logger('EventPoll');

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
  try {
    await api.post(
      '/api/community/events/$eventId/poll/vote/',
      data: {'votes': votes},
    );
    ref.invalidate(eventPollProvider(eventId));
    _log.info('submitted poll vote for event $eventId');
  } catch (e, st) {
    _log.warning('failed to submit poll vote for event $eventId', e, st);
    rethrow;
  }
}

/// Finalizes an event poll by selecting a winning option.
Future<void> finalizeEventPoll({
  required WidgetRef ref,
  required String eventId,
  required String winningOptionId,
}) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.post(
      '/api/community/events/$eventId/poll/finalize/',
      data: {'winning_option_id': winningOptionId},
    );
    ref.invalidate(eventPollProvider(eventId));
    ref.invalidate(eventDetailProvider(eventId));
    ref.invalidate(eventsProvider);
    _log.info('finalized poll for event $eventId with option $winningOptionId');
  } catch (e, st) {
    _log.warning('failed to finalize poll for event $eventId', e, st);
    rethrow;
  }
}

/// Adds a single datetime option to an existing poll.
Future<void> addPollOption({
  required WidgetRef ref,
  required String eventId,
  required DateTime datetime,
}) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.post(
      '/api/community/events/$eventId/poll/options/',
      data: {'datetime': datetime.toUtc().toIso8601String()},
    );
    ref.invalidate(eventPollProvider(eventId));
    _log.info('added poll option to event $eventId');
  } catch (e, st) {
    _log.warning('failed to add poll option to event $eventId', e, st);
    rethrow;
  }
}

/// Removes a single option from an existing poll.
Future<void> deletePollOption({
  required WidgetRef ref,
  required String eventId,
  required String optionId,
}) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.delete('/api/community/events/$eventId/poll/options/$optionId/');
    ref.invalidate(eventPollProvider(eventId));
    _log.info('deleted poll option $optionId from event $eventId');
  } catch (e, st) {
    _log.warning(
      'failed to delete poll option $optionId from event $eventId',
      e,
      st,
    );
    rethrow;
  }
}

/// Updates a single option's datetime on an existing poll.
Future<void> updatePollOption({
  required WidgetRef ref,
  required String eventId,
  required String optionId,
  required DateTime datetime,
}) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.patch(
      '/api/community/events/$eventId/poll/options/$optionId/',
      data: {'datetime': datetime.toUtc().toIso8601String()},
    );
    ref.invalidate(eventPollProvider(eventId));
    _log.info('updated poll option $optionId on event $eventId');
  } catch (e, st) {
    _log.warning(
      'failed to update poll option $optionId on event $eventId',
      e,
      st,
    );
    rethrow;
  }
}

/// Deletes the event poll entirely.
Future<void> deleteEventPoll({
  required WidgetRef ref,
  required String eventId,
}) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.delete('/api/community/events/$eventId/poll/');
    ref.invalidate(eventPollProvider(eventId));
    ref.invalidate(eventDetailProvider(eventId));
    ref.invalidate(eventsProvider);
    _log.info('deleted poll for event $eventId');
  } catch (e, st) {
    _log.warning('failed to delete poll for event $eventId', e, st);
    rethrow;
  }
}

/// Creates an event poll with a list of datetime options.
Future<void> createEventPoll({
  required WidgetRef ref,
  required String eventId,
  required List<DateTime> options,
}) async {
  final api = ref.read(apiClientProvider);
  try {
    await api.post(
      '/api/community/events/$eventId/poll/',
      data: {
        'options': options.map((dt) => dt.toUtc().toIso8601String()).toList(),
      },
    );
    ref.invalidate(eventPollProvider(eventId));
    ref.invalidate(eventDetailProvider(eventId));
    ref.invalidate(eventsProvider);
    _log.info('created poll for event $eventId with ${options.length} options');
  } catch (e, st) {
    _log.warning('failed to create poll for event $eventId', e, st);
    rethrow;
  }
}
