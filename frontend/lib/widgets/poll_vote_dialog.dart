import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/poll_option_widgets.dart';
import 'package:pda/widgets/poll_widgets.dart';

/// Dialog for voting on poll options (yes/maybe per option).
///
/// Pre-fills from existing votes if the user has already voted.
class PollVoteDialog extends ConsumerStatefulWidget {
  final String eventId;
  final EventPoll poll;

  const PollVoteDialog({super.key, required this.eventId, required this.poll});

  @override
  ConsumerState<PollVoteDialog> createState() => _PollVoteDialogState();
}

class _PollVoteDialogState extends ConsumerState<PollVoteDialog> {
  late Map<String, String> _selected;
  bool _submitting = false;

  bool get _hasExistingVotes => widget.poll.myVotes.isNotEmpty;

  @override
  void initState() {
    super.initState();
    _selected = Map.of(widget.poll.myVotes);
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
      await submitPollVote(ref: ref, eventId: widget.eventId, votes: _selected);
      if (mounted) Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) showErrorSnackBar(context, 'couldn\'t submit — try again');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  void _showVoters(EventPollOption option) {
    showModalBottomSheet<void>(
      context: context,
      builder: (ctx) => VotersSheet(
        option: formatPollOption(option.datetime),
        voters: option.allVoters,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final sortedOptions = [...widget.poll.options]
      ..sort((a, b) => b.totalCount.compareTo(a.totalCount));

    return AlertDialog(
      title: const Text('pick a time'),
      contentPadding: const EdgeInsets.fromLTRB(24, 12, 24, 0),
      content: SizedBox(
        width: 380,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
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
                onVotersTap: () => _showVoters(option),
              ),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        FilledButton(
          onPressed: _submitting || _selected.isEmpty ? null : _submit,
          child: Text(
            _submitting
                ? 'submitting...'
                : _hasExistingVotes
                ? 'update vote'
                : 'submit vote',
          ),
        ),
      ],
    );
  }
}
