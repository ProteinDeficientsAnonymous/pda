import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event_poll.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/poll_widgets.dart';

/// Read-only view shown after voting: date label + yes/maybe counts with avatars.
class PollOptionResult extends StatelessWidget {
  final EventPollOption option;
  final VoidCallback onVotersTap;

  const PollOptionResult({
    super.key,
    required this.option,
    required this.onVotersTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            formatPollOption(option.datetime),
            style: theme.textTheme.bodyMedium,
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              PollCountBucket(
                icon: Icons.check_circle_outline,
                count: option.yesCount,
                voters: option.yesVoters.take(3).toList(),
                color: theme.colorScheme.primary,
                onTap: option.yesVoters.isNotEmpty ? onVotersTap : null,
              ),
              const SizedBox(width: 16),
              PollCountBucket(
                icon: Icons.help_outline,
                count: option.maybeCount,
                voters: option.maybeVoters.take(3).toList(),
                color: theme.colorScheme.secondary,
                onTap: option.maybeVoters.isNotEmpty ? onVotersTap : null,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class PollCountBucket extends StatelessWidget {
  final IconData icon;
  final int count;
  final List<PollVoter> voters;
  final Color color;
  final VoidCallback? onTap;

  const PollCountBucket({
    super.key,
    required this.icon,
    required this.count,
    required this.voters,
    required this.color,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Semantics(
        button: onTap != null,
        label: 'see who voted',
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(icon, size: 14, color: color),
            const SizedBox(width: 3),
            Text(
              '$count',
              style: theme.textTheme.bodySmall?.copyWith(color: color),
            ),
            if (voters.isNotEmpty) ...[
              const SizedBox(width: 6),
              VoterAvatarStack(voters: voters),
            ],
          ],
        ),
      ),
    );
  }
}

class PollOptionRow extends StatelessWidget {
  final EventPollOption option;
  final String? availability;
  final bool isEditing;
  final void Function(String availability)? onSetAvailability;
  final VoidCallback onVotersTap;

  const PollOptionRow({
    super.key,
    required this.option,
    required this.availability,
    required this.isEditing,
    required this.onSetAvailability,
    required this.onVotersTap,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final voters = option.allVoters;
    final totalCount = option.totalCount;

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  formatPollOption(option.datetime),
                  style: theme.textTheme.bodyMedium,
                ),
              ),
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
                        VoterAvatarStack(voters: voters),
                        const SizedBox(width: 4),
                        Text(
                          '$totalCount',
                          style: theme.textTheme.bodySmall?.copyWith(
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ),
                  ),
                )
              else if (totalCount > 0)
                Text(
                  '$totalCount',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
            ],
          ),
          const SizedBox(height: 4),
          Row(
            children: [
              AvailabilityChip(
                label: PollAvailability.yes,
                icon: Icons.check_circle_outline,
                isActive: availability == PollAvailability.yes,
                count: option.yesCount,
                onTap: isEditing
                    ? () => onSetAvailability?.call(PollAvailability.yes)
                    : null,
              ),
              const SizedBox(width: 8),
              AvailabilityChip(
                label: PollAvailability.maybe,
                icon: Icons.help_outline,
                isActive: availability == PollAvailability.maybe,
                count: option.maybeCount,
                onTap: isEditing
                    ? () => onSetAvailability?.call(PollAvailability.maybe)
                    : null,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

/// Bottom sheet for picking the winning poll option.
class PollFinalizeSheet extends ConsumerStatefulWidget {
  final EventPoll poll;
  final String eventId;

  const PollFinalizeSheet({
    super.key,
    required this.poll,
    required this.eventId,
  });

  @override
  ConsumerState<PollFinalizeSheet> createState() => _PollFinalizeSheetState();
}

class _PollFinalizeSheetState extends ConsumerState<PollFinalizeSheet> {
  String? _selected;
  bool _submitting = false;

  Future<void> _confirm() async {
    if (_selected == null) return;
    setState(() => _submitting = true);
    try {
      await finalizeEventPoll(
        ref: ref,
        eventId: widget.eventId,
        winningOptionId: _selected!,
      );
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) showErrorSnackBar(context, 'couldn\'t finalize — try again');
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final options = [...widget.poll.options]
      ..sort((a, b) => a.datetime.compareTo(b.datetime));

    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('choose the winning time', style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              'this sets the event date and closes the poll',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
              ),
            ),
            const SizedBox(height: 12),
            ...options.map(
              (option) => InkWell(
                onTap: () => setState(() => _selected = option.id),
                borderRadius: BorderRadius.circular(8),
                child: Semantics(
                  button: true,
                  label: formatPollOption(option.datetime),
                  child: Padding(
                    padding: const EdgeInsets.symmetric(vertical: 6),
                    child: Row(
                      children: [
                        Icon(
                          _selected == option.id
                              ? Icons.radio_button_checked
                              : Icons.radio_button_unchecked,
                          size: 20,
                          color: _selected == option.id
                              ? theme.colorScheme.primary
                              : theme.colorScheme.onSurfaceVariant,
                        ),
                        const SizedBox(width: 10),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(formatPollOption(option.datetime)),
                              Text(
                                '${option.yesCount} yes · ${option.maybeCount} maybe',
                                style: theme.textTheme.bodySmall?.copyWith(
                                  color: theme.colorScheme.onSurfaceVariant,
                                ),
                              ),
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
              ),
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                FilledButton(
                  onPressed: _submitting || _selected == null ? null : _confirm,
                  child: Text(_submitting ? 'finalizing...' : 'confirm'),
                ),
                const SizedBox(width: 8),
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('cancel'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
