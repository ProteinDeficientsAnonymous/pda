import 'package:dio/dio.dart';
import 'package:flutter/painting.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('EventProvider');

final eventsProvider = FutureProvider<List<Event>>((ref) async {
  ref.watch(authProvider);
  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get('/api/community/events/');
    final list = response.data as List<dynamic>;
    final events = list
        .map((e) => Event.fromJson(e as Map<String, dynamic>))
        .toList();
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

Future<void> uploadEventPhoto(
  WidgetRef ref,
  String eventId,
  XFile file, {
  String? oldPhotoUrl,
}) async {
  final api = ref.read(apiClientProvider);
  final bytes = await file.readAsBytes();
  final formData = FormData.fromMap({
    'photo': MultipartFile.fromBytes(bytes, filename: file.name),
  });
  await api.post('/api/community/events/$eventId/photo/', data: formData);
  if (oldPhotoUrl != null && oldPhotoUrl.isNotEmpty) {
    imageCache.evict(NetworkImage(oldPhotoUrl));
  }
  ref.invalidate(eventsProvider);
  ref.invalidate(draftEventsProvider);
  ref.invalidate(eventDetailProvider(eventId));
}

Future<void> deleteEventPhoto(WidgetRef ref, String eventId) async {
  final api = ref.read(apiClientProvider);
  await api.delete('/api/community/events/$eventId/photo/');
  ref.invalidate(eventsProvider);
  ref.invalidate(draftEventsProvider);
  ref.invalidate(eventDetailProvider(eventId));
}

Future<void> patchEventStatus(
  WidgetRef ref,
  String eventId, {
  required String status,
  bool? notifyAttendees,
}) async {
  final api = ref.read(apiClientProvider);
  final data = <String, dynamic>{'status': status};
  if (notifyAttendees != null) {
    data['notify_attendees'] = notifyAttendees;
  }
  await api.patch('/api/community/events/$eventId/', data: data);
  ref.invalidate(eventsProvider);
  ref.invalidate(cancelledEventsProvider);
  ref.invalidate(draftEventsProvider);
  ref.invalidate(eventDetailProvider(eventId));
}

final cancelledEventsProvider = FutureProvider<List<Event>>((ref) async {
  ref.watch(authProvider);
  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get(
      '/api/community/events/',
      queryParameters: {'status': 'cancelled'},
    );
    final list = response.data as List<dynamic>;
    return list.map((e) => Event.fromJson(e as Map<String, dynamic>)).toList();
  } catch (e) {
    _log.warning('Failed to load cancelled events', e);
    rethrow;
  }
});

final draftEventsProvider = FutureProvider<List<Event>>((ref) async {
  ref.watch(authProvider);
  final api = ref.watch(apiClientProvider);
  try {
    final response = await api.get(
      '/api/community/events/',
      queryParameters: {'status': 'draft'},
    );
    final list = response.data as List<dynamic>;
    return list.map((e) => Event.fromJson(e as Map<String, dynamic>)).toList();
  } catch (e) {
    _log.warning('Failed to load draft events', e);
    rethrow;
  }
});
