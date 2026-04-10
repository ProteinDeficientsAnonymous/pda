import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/widgets/poll_widgets.dart';
import 'package:pda/widgets/poll_option_widgets.dart';
import 'package:pda/widgets/poll_vote_dialog.dart';

/// Renders an EventPoll inline inside the event detail "when" section card.
///
/// Shows read-only results with a button to vote/edit vote via a dialog.
/// Admin "choose winner" and finalized views remain inline.
class EmbeddedEventPoll extends ConsumerWidget {
  final Event event;

  const EmbeddedEventPoll({super.key, required this.event});

  bool _canManagePoll(User user) {
    if (user.hasPermission(Permission.manageEvents)) return true;
    if (user.hasPermission(Permission.manageSurveys)) return true;
    if (event.createdById == user.id) return true;
    if (event.coHostIds.contains(user.id)) return true;
    return false;
  }

  void _showFinalizeSheet(BuildContext context, EventPoll poll) {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => PollFinalizeSheet(poll: poll, eventId: event.id),
    );
  }

  void _showVoters(BuildContext context, EventPollOption option) {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => VotersSheet(
        option: formatPollOption(option.datetime),
        voters: option.allVoters,
      ),
    );
  }

  void _openVoteDialog(BuildContext context, EventPoll poll) {
    showDialog<bool>(
      context: context,
      builder: (_) => PollVoteDialog(eventId: event.id, poll: poll),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final pollAsync = ref.watch(eventPollProvider(event.id));

    return pollAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => const Text('date & time tbd'),
      data: (poll) {
        if (poll == null) return const Text('date & time tbd');

        if (poll.isFinalized) return _buildFinalized(poll.winningDatetime!);

        final user = ref.watch(authProvider).value;
        if (user == null) {
          return Text(
            'sign in to vote on a time 🌿',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          );
        }

        final isPast = event.isPast;
        final canManage = !isPast && _canManagePoll(user);
        final hasVoted = poll.myVotes.isNotEmpty;
        final sortedOptions = [...poll.options]
          ..sort((a, b) => b.totalCount.compareTo(a.totalCount));

        return _buildResultsView(
          context,
          theme,
          poll,
          sortedOptions,
          hasVoted,
          canManage,
          isPast: isPast,
        );
      },
    );
  }

  Widget _buildFinalized(DateTime winningUtc) {
    final winning = winningUtc.toLocal();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          DateFormat('EEEE, MMMM d').format(winning),
          style: const TextStyle(fontSize: 15, height: 1.4),
        ),
        Text(
          DateFormat('h:mm a').format(winning).toLowerCase(),
          style: const TextStyle(fontSize: 15, height: 1.4),
        ),
      ],
    );
  }

  Widget _buildResultsView(
    BuildContext context,
    ThemeData theme,
    EventPoll poll,
    List<EventPollOption> sortedOptions,
    bool hasVoted,
    bool canManage, {
    bool isPast = false,
  }) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (hasVoted || isPast) ...[
          if (!isPast) Text('you voted ✓', style: theme.textTheme.labelLarge),
          if (isPast) Text('poll closed', style: theme.textTheme.labelLarge),
          const SizedBox(height: 4),
          ...sortedOptions.map(
            (option) => PollOptionResult(
              option: option,
              onVotersTap: () => _showVoters(context, option),
            ),
          ),
          if (!isPast) ...[
            const SizedBox(height: 8),
            Row(
              children: [
                Semantics(
                  button: true,
                  label: 'edit your poll response',
                  child: OutlinedButton(
                    onPressed: () => _openVoteDialog(context, poll),
                    child: const Text('edit response'),
                  ),
                ),
                if (canManage) ...[
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () => _showFinalizeSheet(context, poll),
                    child: const Text('choose winner'),
                  ),
                ],
              ],
            ),
          ],
        ] else ...[
          Text('time poll open', style: theme.textTheme.labelLarge),
          const SizedBox(height: 4),
          Text(
            '${poll.options.length} options · vote to help pick a time',
            style: theme.textTheme.bodySmall?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 8),
          Semantics(
            button: true,
            label: 'respond to poll',
            child: FilledButton(
              onPressed: () => _openVoteDialog(context, poll),
              child: const Text('respond to poll'),
            ),
          ),
          if (canManage) ...[
            const SizedBox(height: 4),
            TextButton(
              onPressed: () => _showFinalizeSheet(context, poll),
              style: TextButton.styleFrom(
                padding: EdgeInsets.zero,
                tapTargetSize: MaterialTapTargetSize.shrinkWrap,
              ),
              child: Text(
                'choose winner',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ),
          ],
        ],
      ],
    );
  }
}
