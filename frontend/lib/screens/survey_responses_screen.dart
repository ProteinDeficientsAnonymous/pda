import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/poll_provider.dart';
import 'package:pda/providers/survey_admin_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';

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
        error:
            (e, _) => const Center(
              child: Text('couldn\'t load responses — try refreshing'),
            ),
        data: (responses) {
          final survey = surveyAsync.valueOrNull;
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
          _PollTallySection(surveyId: surveyId, survey: survey!),
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

class _PollTallySection extends ConsumerStatefulWidget {
  final String surveyId;
  final Survey survey;

  const _PollTallySection({required this.surveyId, required this.survey});

  @override
  ConsumerState<_PollTallySection> createState() => _PollTallySectionState();
}

class _PollTallySectionState extends ConsumerState<_PollTallySection> {
  bool _finalizing = false;

  Future<void> _confirmFinalize(DateTime winningDt) async {
    final fmt = DateFormat('EEE, MMM d · h:mm a').format(winningDt.toLocal());
    final confirmed = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('choose this time?'),
            content: Text(
              '${fmt.toLowerCase()}\n\nThis will set the event date and close the poll. This cannot be undone.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('confirm'),
              ),
            ],
          ),
    );
    if (confirmed != true || !mounted) return;

    setState(() => _finalizing = true);
    try {
      await finalizePoll(
        ref: ref,
        surveyId: widget.surveyId,
        winningDatetime: winningDt,
      );
      ref.invalidate(surveyQuestionsProvider(widget.surveyId));
      ref.invalidate(surveyResponsesProvider(widget.surveyId));
      if (mounted) showSnackBar(context, 'time chosen! 🎉');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t finalize — try again');
      }
    } finally {
      if (mounted) setState(() => _finalizing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final talliesAsync = ref.watch(pollTalliesProvider(widget.surveyId));
    final isFinalized = widget.survey.pollResult != null;

    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              const Icon(Icons.how_to_vote_outlined, size: 18),
              const SizedBox(width: 8),
              Text('poll results', style: theme.textTheme.titleSmall),
              if (isFinalized) ...[
                const SizedBox(width: 8),
                Container(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 8,
                    vertical: 2,
                  ),
                  decoration: BoxDecoration(
                    color: theme.colorScheme.primaryContainer,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Text(
                    'finalized',
                    style: TextStyle(
                      fontSize: 11,
                      color: theme.colorScheme.onPrimaryContainer,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                ),
              ],
            ],
          ),
          if (!isFinalized) ...[
            const SizedBox(height: 4),
            Text(
              'tap "choose this time" to finalize the event date',
              style: TextStyle(
                fontSize: 12,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
              ),
            ),
          ],
          const SizedBox(height: 12),
          talliesAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error:
                (_, __) => const Text(
                  'couldn\'t load tallies',
                  style: TextStyle(color: Colors.grey),
                ),
            data: (tallies) {
              final pollQuestions =
                  widget.survey.questions
                      .where((q) => q.fieldType == FieldType.datetimePoll)
                      .toList();

              return Column(
                children:
                    pollQuestions.map((q) {
                      final tally =
                          tallies
                              .where((t) => t.questionId == q.id)
                              .firstOrNull;
                      final total = tally?.totalResponses ?? 0;
                      final winnerIso =
                          widget.survey.pollResult?.winningDatetime
                              .toUtc()
                              .toIso8601String();

                      return Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          if (pollQuestions.length > 1) ...[
                            Text(
                              q.label,
                              style: const TextStyle(
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 8),
                          ],
                          ...q.options.map((iso) {
                            final count = tally?.tallies[iso] ?? 0;
                            final fraction = total > 0 ? count / total : 0.0;
                            final label = _formatPollOptionShort(iso);
                            final isWinner =
                                winnerIso != null &&
                                _normalizeIsoStr(iso) ==
                                    _normalizeIsoStr(winnerIso);

                            return Padding(
                              padding: const EdgeInsets.only(bottom: 8),
                              child: Row(
                                children: [
                                  Expanded(
                                    child: Column(
                                      crossAxisAlignment:
                                          CrossAxisAlignment.start,
                                      children: [
                                        Row(
                                          children: [
                                            Expanded(
                                              child: Text(
                                                label,
                                                style: TextStyle(
                                                  fontSize: 13,
                                                  fontWeight:
                                                      isWinner
                                                          ? FontWeight.w600
                                                          : FontWeight.normal,
                                                ),
                                              ),
                                            ),
                                            if (isWinner)
                                              Icon(
                                                Icons.check_circle_rounded,
                                                size: 14,
                                                color:
                                                    theme.colorScheme.primary,
                                              ),
                                            const SizedBox(width: 4),
                                            Text(
                                              '$count',
                                              style: TextStyle(
                                                fontSize: 13,
                                                color: theme
                                                    .colorScheme
                                                    .onSurface
                                                    .withValues(alpha: 0.6),
                                              ),
                                            ),
                                          ],
                                        ),
                                        const SizedBox(height: 4),
                                        ClipRRect(
                                          borderRadius: BorderRadius.circular(
                                            3,
                                          ),
                                          child: LinearProgressIndicator(
                                            value: fraction,
                                            minHeight: 5,
                                            backgroundColor: theme
                                                .colorScheme
                                                .outline
                                                .withValues(alpha: 0.15),
                                            color:
                                                isWinner
                                                    ? theme.colorScheme.primary
                                                    : theme
                                                        .colorScheme
                                                        .secondary,
                                          ),
                                        ),
                                      ],
                                    ),
                                  ),
                                  if (!isFinalized) ...[
                                    const SizedBox(width: 12),
                                    _finalizing
                                        ? const SizedBox(
                                          width: 16,
                                          height: 16,
                                          child: CircularProgressIndicator(
                                            strokeWidth: 2,
                                          ),
                                        )
                                        : TextButton(
                                          onPressed:
                                              () => _confirmFinalize(
                                                DateTime.parse(iso),
                                              ),
                                          style: TextButton.styleFrom(
                                            padding: const EdgeInsets.symmetric(
                                              horizontal: 8,
                                              vertical: 4,
                                            ),
                                            minimumSize: Size.zero,
                                            tapTargetSize:
                                                MaterialTapTargetSize
                                                    .shrinkWrap,
                                          ),
                                          child: const Text(
                                            'choose this time',
                                            style: TextStyle(fontSize: 12),
                                          ),
                                        ),
                                  ],
                                ],
                              ),
                            );
                          }),
                        ],
                      );
                    }).toList(),
              );
            },
          ),
        ],
      ),
    );
  }
}

String _formatPollOptionShort(String iso) {
  try {
    final dt = DateTime.parse(iso).toLocal();
    return DateFormat('EEE, MMM d · h:mm a').format(dt).toLowerCase();
  } catch (_) {
    return iso;
  }
}

String _normalizeIsoStr(String iso) {
  try {
    return DateTime.parse(iso).toUtc().toIso8601String();
  } catch (_) {
    return iso;
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
