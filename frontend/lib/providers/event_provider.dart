import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';

final eventsProvider = FutureProvider<List<Event>>((ref) async {
  final api = ref.watch(apiClientProvider);
  final response = await api.get('/api/community/events/');
  final list = response.data as List<dynamic>;
  return list.map((e) => Event.fromJson(e as Map<String, dynamic>)).toList();
});
