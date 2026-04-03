import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/poll_provider.dart';
import 'package:pda/screens/survey_poll_results.dart';

/// Formats an ISO 8601 datetime string for display in a poll option.
String formatPollOption(String iso) {
  try {
    final dt = DateTime.parse(iso).toLocal();
    return DateFormat('EEE, MMM d · h:mm a').format(dt).toLowerCase();
  } catch (_) {
    return iso;
  }
}

/// Normalises an ISO 8601 string for comparison (strips trailing Z vs +00:00 etc.)
String normalizeIso(String iso) {
  try {
    return DateTime.parse(iso).toUtc().toIso8601String();
  } catch (_) {
    return iso;
  }
}

class SurveyDatetimePollField extends ConsumerStatefulWidget {
  final SurveyQuestion question;
  final Survey survey;
  final bool isFinalized;
  final FormFieldValidator<String> validator;
  final FormFieldSetter<String> onSaved;

  const SurveyDatetimePollField({
    super.key,
    required this.question,
    required this.survey,
    required this.isFinalized,
    required this.validator,
    required this.onSaved,
  });

  @override
  ConsumerState<SurveyDatetimePollField> createState() =>
      _SurveyDatetimePollFieldState();
}

class _SurveyDatetimePollFieldState
    extends ConsumerState<SurveyDatetimePollField> {
  // Maps ISO option -> "yes" or "maybe"
  late Map<String, String> _selected;

  @override
  void initState() {
    super.initState();
    final myAnswers = widget.survey.myAnswers;
    if (myAnswers != null) {
      final answerData = myAnswers[widget.question.id] as Map<String, dynamic>?;
      final answer = answerData?['answer'];
      if (answer is Map<String, dynamic>) {
        _selected = answer.map((k, v) => MapEntry(k, v as String));
      } else {
        _selected = {};
      }
    } else {
      _selected = {};
    }
  }

  String _encodeSelected() {
    return _selected.entries.map((e) => '${e.key}:${e.value}').join(',');
  }

  void _setAvailability(
    String iso,
    String availability,
    FormFieldState<String> state,
  ) {
    setState(() {
      if (_selected[iso] == availability) {
        _selected = Map.of(_selected)..remove(iso);
      } else {
        _selected = {..._selected, iso: availability};
      }
      state.didChange(_encodeSelected());
    });
  }

  Widget _buildOption(
    BuildContext context,
    String iso,
    PollResults? results,
    String? winnerIso,
    FormFieldState<String> state,
  ) {
    final label = formatPollOption(iso);
    final totalCount = results?.totalForOption(iso) ?? 0;
    final total = results?.totalResponses ?? 0;
    final voters = results?.voters[iso] ?? [];
    final counts = results?.tallies[iso] ?? {};
    final yesCount = counts['yes'] ?? 0;
    final maybeCount = counts['maybe'] ?? 0;
    final isWinner =
        winnerIso != null && normalizeIso(iso) == normalizeIso(winnerIso);

    if (widget.isFinalized) {
      return SurveyPollOptionResult(
        label: label,
        count: totalCount,
        total: total,
        isWinner: isWinner,
      );
    }

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SurveyPollOptionTitle(
            label: label,
            count: totalCount,
            voters: voters,
            onVotersTap: voters.isNotEmpty
                ? () => _showVoters(context, label, voters)
                : null,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              SurveyAvailabilityChip(
                label: 'yes',
                icon: Icons.check_circle_outline,
                isActive: _selected[iso] == 'yes',
                count: yesCount,
                onTap: () => _setAvailability(iso, 'yes', state),
              ),
              const SizedBox(width: 8),
              SurveyAvailabilityChip(
                label: 'maybe',
                icon: Icons.help_outline,
                isActive: _selected[iso] == 'maybe',
                count: maybeCount,
                onTap: () => _setAvailability(iso, 'maybe', state),
              ),
            ],
          ),
        ],
      ),
    );
  }

  void _showVoters(BuildContext context, String label, List<PollVoter> voters) {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => SafeArea(
        child: Padding(
          padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(label, style: Theme.of(ctx).textTheme.titleMedium),
              const SizedBox(height: 4),
              Text(
                '${voters.length} vote${voters.length == 1 ? '' : 's'}',
                style: Theme.of(ctx).textTheme.bodySmall?.copyWith(
                  color: Theme.of(ctx).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 12),
              for (final voter in voters)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 6),
                  child: Row(
                    children: [
                      CircleAvatar(
                        radius: 16,
                        backgroundImage: voter.photoUrl.isNotEmpty
                            ? NetworkImage(voter.photoUrl)
                            : null,
                        child: voter.photoUrl.isEmpty
                            ? Text(
                                voter.name.isNotEmpty
                                    ? voter.name[0].toUpperCase()
                                    : '?',
                                style: const TextStyle(fontSize: 12),
                              )
                            : null,
                      ),
                      const SizedBox(width: 12),
                      Text(voter.name),
                    ],
                  ),
                ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final resultsAsync = ref.watch(pollResultsProvider(widget.survey.id));
    final allResults = resultsAsync.value;
    final questionResults = allResults
        ?.where((t) => t.questionId == widget.question.id)
        .firstOrNull;
    final winnerIso = widget.survey.pollResult?.winningDatetime
        .toUtc()
        .toIso8601String();

    return FormField<String>(
      initialValue: '',
      validator: widget.validator,
      onSaved: (_) => widget.onSaved(_encodeSelected()),
      builder: (state) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${widget.question.label}${widget.question.required ? ' *' : ''}',
            ),
            const SizedBox(height: 8),
            if (!widget.isFinalized)
              Text(
                'for each option, mark yes or maybe',
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
            const SizedBox(height: 8),
            ...widget.question.options.map(
              (iso) =>
                  _buildOption(context, iso, questionResults, winnerIso, state),
            ),
            if (state.hasError)
              Padding(
                padding: const EdgeInsets.only(left: 12, top: 4),
                child: Text(
                  state.errorText!,
                  style: TextStyle(
                    color: theme.colorScheme.error,
                    fontSize: 12,
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class SurveyAvailabilityChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isActive;
  final int count;
  final VoidCallback? onTap;

  const SurveyAvailabilityChip({
    super.key,
    required this.label,
    required this.icon,
    required this.isActive,
    required this.count,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = isActive
        ? theme.colorScheme.primary
        : theme.colorScheme.outline;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Semantics(
        button: onTap != null,
        label: '$label${isActive ? ' selected' : ''}',
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(color: color),
            color: isActive ? color.withValues(alpha: 0.1) : null,
          ),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(icon, size: 16, color: color),
              const SizedBox(width: 4),
              Text(
                count > 0 ? '$label ($count)' : label,
                style: theme.textTheme.bodySmall?.copyWith(color: color),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class SurveyPollOptionTitle extends StatelessWidget {
  final String label;
  final int count;
  final List<PollVoter> voters;
  final VoidCallback? onVotersTap;

  const SurveyPollOptionTitle({
    super.key,
    required this.label,
    required this.count,
    required this.voters,
    this.onVotersTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Row(
      children: [
        Expanded(child: Text(label)),
        if (voters.isNotEmpty)
          InkWell(
            onTap: onVotersTap,
            borderRadius: BorderRadius.circular(12),
            child: Semantics(
              button: true,
              label: 'see who voted',
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  SurveyVoterAvatarStack(voters: voters),
                  const SizedBox(width: 4),
                  Text(
                    '$count',
                    style: theme.textTheme.bodySmall?.copyWith(
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          )
        else if (count > 0)
          Text(
            '$count',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
      ],
    );
  }
}
