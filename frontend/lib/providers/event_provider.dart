import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('EventProvider');

final eventsProvider = FutureProvider<List<Event>>((ref) async {
  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get('/api/community/events/');
    final list = response.data as List<dynamic>;
    final events =
        list.map((e) => Event.fromJson(e as Map<String, dynamic>)).toList();
    _log.info('Loaded ${events.length} events');
    return events;
  } catch (e) {
    _log.warning('Failed to load events', e);
    rethrow;
  }
});

final eventDetailProvider = FutureProvider.family<Event, String>((
  ref,
  eventId,
) async {
  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get('/api/community/events/$eventId/');
    return Event.fromJson(response.data as Map<String, dynamic>);
  } catch (e) {
    _log.warning('Failed to load event $eventId', e);
    rethrow;
  }
});
