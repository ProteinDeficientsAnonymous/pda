import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/survey_admin_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/screens/survey_poll_results_section.dart';

class SurveyResponsesScreen extends ConsumerWidget {
  final String surveyId;

  const SurveyResponsesScreen({super.key, required this.surveyId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final responsesAsync = ref.watch(surveyResponsesProvider(surveyId));
    final surveyAsync = ref.watch(surveyQuestionsProvider(surveyId));

    return AppScaffold(
      child: responsesAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => const Center(
          child: Text('couldn\'t load responses — try refreshing'),
        ),
        data: (responses) {
          final survey = surveyAsync.value;
          return _ResponsesBody(
            surveyId: surveyId,
            survey: survey,
            responses: responses,
          );
        },
      ),
    );
  }
}

class _ResponsesBody extends ConsumerWidget {
  final String surveyId;
  final Survey? survey;
  final List<SurveyResponse> responses;

  const _ResponsesBody({
    required this.surveyId,
    required this.survey,
    required this.responses,
  });

  bool get _hasPollQuestion =>
      survey?.questions.any((q) => q.fieldType == FieldType.datetimePoll) ??
      false;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final dateFmt = DateFormat('MMM d, y h:mm a');
    final questions = survey?.questions ?? [];

    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Text(
          '${survey?.title ?? 'survey'} — responses',
          style: theme.textTheme.headlineSmall,
        ),
        const SizedBox(height: 4),
        Text(
          '${responses.length} responses',
          style: TextStyle(
            color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
          ),
        ),
        if (_hasPollQuestion) ...[
          const SizedBox(height: 20),
          SurveyPollResultsSection(surveyId: surveyId, survey: survey!),
        ],
        const SizedBox(height: 20),
        if (responses.isEmpty)
          Center(
            child: Padding(
              padding: const EdgeInsets.only(top: 48),
              child: Column(
                children: [
                  Icon(
                    Icons.inbox_outlined,
                    size: 48,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
                  ),
                  const SizedBox(height: 12),
                  Text(
                    'no responses yet 🌿',
                    style: theme.textTheme.bodyLarge?.copyWith(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                    ),
                  ),
                ],
              ),
            ),
          )
        else
          ...responses.map(
            (r) => _ResponseCard(
              response: r,
              questions: questions,
              dateFmt: dateFmt,
            ),
          ),
      ],
    );
  }
}

class _ResponseCard extends StatelessWidget {
  final SurveyResponse response;
  final List<SurveyQuestion> questions;
  final DateFormat dateFmt;

  const _ResponseCard({
    required this.response,
    required this.questions,
    required this.dateFmt,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(
                  Icons.person_outline,
                  size: 16,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                ),
                const SizedBox(width: 6),
                Text(
                  response.userName ?? 'anonymous',
                  style: TextStyle(
                    fontWeight: FontWeight.w600,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.7),
                  ),
                ),
                const Spacer(),
                Text(
                  dateFmt.format(response.submittedAt.toLocal()).toLowerCase(),
                  style: TextStyle(
                    fontSize: 12,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
                  ),
                ),
              ],
            ),
            const Divider(height: 20),
            ...response.answers.entries.map((entry) {
              final data = entry.value as Map<String, dynamic>;
              final label = data['label'] as String? ?? entry.key;
              final answer = data['answer'] as String? ?? '';
              return Padding(
                padding: const EdgeInsets.only(bottom: 8),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      label,
                      style: TextStyle(
                        fontSize: 12,
                        fontWeight: FontWeight.w600,
                        color: theme.colorScheme.onSurface.withValues(
                          alpha: 0.5,
                        ),
                      ),
                    ),
                    const SizedBox(height: 2),
                    Text(answer),
                  ],
                ),
              );
            }),
          ],
        ),
      ),
    );
  }
}
