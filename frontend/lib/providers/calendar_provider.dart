import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';

final calendarTokenProvider = FutureProvider<String>((ref) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/api/community/calendar/token/');
  final data = resp.data as Map<String, dynamic>;
  return (data['token'] as String?) ?? '';
});

/// Generates (or regenerates) a calendar token and returns the feed URL.
Future<String> generateCalendarToken(Ref ref) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.post('/api/community/calendar/token/');
  final data = resp.data as Map<String, dynamic>;
  ref.invalidate(calendarTokenProvider);
  return data['feed_url'] as String;
}
