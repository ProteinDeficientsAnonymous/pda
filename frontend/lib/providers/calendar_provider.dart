import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';

final _log = Logger('Calendar');

final calendarTokenProvider = FutureProvider<String>((ref) async {
  final api = ref.read(apiClientProvider);
  final resp = await api.get('/api/community/calendar/token/');
  final data = resp.data as Map<String, dynamic>;
  return (data['token'] as String?) ?? '';
});

/// Generates (or regenerates) a calendar token and returns the feed URL.
Future<String> generateCalendarToken(Ref ref) async {
  final api = ref.read(apiClientProvider);
  try {
    final resp = await api.post('/api/community/calendar/token/');
    final data = resp.data as Map<String, dynamic>;
    ref.invalidate(calendarTokenProvider);
    _log.info('generated calendar subscription token');
    return data['feed_url'] as String;
  } catch (e, st) {
    _log.warning('failed to generate calendar subscription token', e, st);
    rethrow;
  }
}
