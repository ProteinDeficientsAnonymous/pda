import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/poll_widgets.dart';
import 'package:pda/widgets/poll_option_widgets.dart';

/// Renders an EventPoll inline inside the event detail "when" section card.
///
/// Shows voting chips when active, results when finalized, and a "sign in"
/// prompt for unauthenticated users.
class EmbeddedEventPoll extends ConsumerStatefulWidget {
  final Event event;

  const EmbeddedEventPoll({super.key, required this.event});

  @override
  ConsumerState<EmbeddedEventPoll> createState() => _EmbeddedEventPollState();
}

class _EmbeddedEventPollState extends ConsumerState<EmbeddedEventPoll> {
  // Maps optionId -> "yes" | "maybe"
  Map<String, String> _selected = {};
  bool _submitting = false;
  bool _editing = false;
  bool _prefilled = false;

  void _prefillFromPoll(EventPoll poll) {
    if (_prefilled || poll.myVotes.isEmpty) return;
    _selected = Map.of(poll.myVotes);
    _prefilled = true;
  }

  void _pruneStaleSelections(EventPoll poll) {
    final validIds = {for (final o in poll.options) o.id};
    final stale = _selected.keys.where((id) => !validIds.contains(id)).toList();
    if (stale.isEmpty) return;
    setState(() {
      for (final id in stale) {
        _selected.remove(id);
      }
    });
  }

  void _setAvailability(String optionId, String availability) {
    setState(() {
      if (_selected[optionId] == availability) {
        _selected = Map.of(_selected)..remove(optionId);
      } else {
        _selected = {..._selected, optionId: availability};
      }
    });
  }

  Future<void> _submit() async {
    if (_selected.isEmpty) return;
    setState(() => _submitting = true);
    try {
      await submitPollVote(
        ref: ref,
        eventId: widget.event.id,
        votes: _selected,
      );
      if (mounted) setState(() => _editing = false);
    } catch (e) {
      if (mounted) showErrorSnackBar(context, 'couldn\'t submit — try again');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
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

  bool _canManagePoll(User user) {
    if (user.hasPermission(Permission.manageEvents)) return true;
    if (user.hasPermission(Permission.manageSurveys)) return true;
    if (widget.event.createdById == user.id) return true;
    if (widget.event.coHostIds.contains(user.id)) return true;
    return false;
  }

  void _showFinalizeSheet(EventPoll poll) {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => PollFinalizeSheet(poll: poll, eventId: widget.event.id),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final pollAsync = ref.watch(eventPollProvider(widget.event.id));

    return pollAsync.when(
      loading: () => const Padding(
        padding: EdgeInsets.symmetric(vertical: 8),
        child: Center(child: CircularProgressIndicator()),
      ),
      error: (_, __) => const Text('date & time tbd'),
      data: (poll) {
        if (poll == null) return const Text('date & time tbd');

        _prefillFromPoll(poll);
        _pruneStaleSelections(poll);

        if (poll.isFinalized) {
          return _buildFinalized(poll.winningDatetime!);
        }

        final user = ref.watch(authProvider).value;
        if (user == null) {
          return Text(
            'sign in to vote on a time 🌿',
            style: theme.textTheme.bodyMedium?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          );
        }

        final canManage = _canManagePoll(user);

        // Sort options by total vote count descending (most popular first)
        final sortedOptions = [...poll.options]
          ..sort((a, b) => b.totalCount.compareTo(a.totalCount));

        final hasVoted = poll.myVotes.isNotEmpty;
        if (hasVoted && !_editing) {
          return _buildVotedView(theme, poll, sortedOptions, canManage);
        }
        return _buildVotingForm(
          theme,
          poll,
          hasVoted,
          sortedOptions,
          canManage,
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

  Widget _buildVotedView(
    ThemeData theme,
    EventPoll poll,
    List<EventPollOption> sortedOptions,
    bool canManage,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            Text('you voted ✓', style: theme.textTheme.labelLarge),
            const Spacer(),
            if (canManage)
              TextButton(
                onPressed: () => _showFinalizeSheet(poll),
                child: const Text('choose winner'),
              )
            else
              TextButton(
                onPressed: () => setState(() => _editing = true),
                child: const Text('edit vote'),
              ),
          ],
        ),
        const SizedBox(height: 4),
        ...sortedOptions.map(
          (option) => PollOptionResult(
            option: option,
            onVotersTap: () => _showVoters(context, option),
          ),
        ),
        if (canManage) ...[
          const SizedBox(height: 4),
          TextButton(
            onPressed: () => setState(() => _editing = true),
            style: TextButton.styleFrom(
              padding: EdgeInsets.zero,
              tapTargetSize: MaterialTapTargetSize.shrinkWrap,
            ),
            child: Text(
              'edit vote',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildVotingForm(
    ThemeData theme,
    EventPoll poll,
    bool hasVoted,
    List<EventPollOption> sortedOptions,
    bool canManage,
  ) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('pick a time', style: theme.textTheme.labelLarge),
        const SizedBox(height: 4),
        Text(
          'for each option, mark yes or maybe',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 8),
        ...sortedOptions.map(
          (option) => PollOptionRow(
            option: option,
            availability: _selected[option.id],
            isEditing: true,
            onSetAvailability: (a) => _setAvailability(option.id, a),
            onVotersTap: () => _showVoters(context, option),
          ),
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            FilledButton(
              onPressed: _submitting || _selected.isEmpty
                  ? null
                  : () => _submit(),
              child: Text(
                _submitting
                    ? 'submitting...'
                    : hasVoted
                    ? 'update vote'
                    : 'submit vote',
              ),
            ),
            if (hasVoted) ...[
              const SizedBox(width: 8),
              TextButton(
                onPressed: () => setState(() => _editing = false),
                child: const Text('cancel'),
              ),
            ],
          ],
        ),
        if (canManage) ...[
          const SizedBox(height: 4),
          TextButton(
            onPressed: () => _showFinalizeSheet(poll),
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
    );
  }
}
