import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/auth_provider.dart';

/// Fetches vote tallies for a datetime poll survey.
final pollTalliesProvider = FutureProvider.family<List<PollTally>, String>((
  ref,
  surveyId,
) async {
  final api = ref.watch(apiClientProvider);
  final response = await api.get('/api/community/surveys/$surveyId/tallies/');
  return (response.data as List<dynamic>)
      .map((e) => PollTally.fromJson(e as Map<String, dynamic>))
      .toList();
});

/// Finalizes a datetime poll by choosing a winning datetime.
/// Returns the updated [Survey] after finalization.
Future<void> finalizePoll({
  required WidgetRef ref,
  required String surveyId,
  required DateTime winningDatetime,
}) async {
  final api = ref.read(apiClientProvider);
  await api.post(
    '/api/community/surveys/$surveyId/finalize/',
    data: {'winning_datetime': winningDatetime.toUtc().toIso8601String()},
  );
  ref.invalidate(pollTalliesProvider(surveyId));
}
