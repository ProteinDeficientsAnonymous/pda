import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event_poll.dart';

export 'package:pda/models/event_poll.dart' show PollVoter;

String formatPollOption(DateTime dt) {
  return DateFormat('EEE, MMM d · h:mm a').format(dt.toLocal()).toLowerCase();
}

/// A yes/maybe availability toggle chip used in poll voting UI.
class AvailabilityChip extends StatelessWidget {
  final String label;
  final IconData icon;
  final bool isActive;
  final int count;
  final VoidCallback? onTap;

  const AvailabilityChip({
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

/// A stack of overlapping voter avatar circles.
class VoterAvatarStack extends StatelessWidget {
  final List<PollVoter> voters;

  const VoterAvatarStack({super.key, required this.voters});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    const size = 22.0;
    const overlap = 8.0;
    const maxShow = 4;
    final showing = voters.take(maxShow).toList();
    final extra = voters.length - showing.length;

    return SizedBox(
      height: size,
      width:
          showing.length * (size - overlap) + overlap + (extra > 0 ? size : 0),
      child: Stack(
        children: [
          for (var i = 0; i < showing.length; i++)
            Positioned(
              left: i * (size - overlap),
              child: CircleAvatar(
                radius: size / 2,
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
                backgroundImage: showing[i].photoUrl.isNotEmpty
                    ? NetworkImage(showing[i].photoUrl)
                    : null,
                child: showing[i].photoUrl.isEmpty
                    ? Text(
                        showing[i].name.isNotEmpty
                            ? showing[i].name[0].toUpperCase()
                            : '?',
                        style: TextStyle(
                          fontSize: 10,
                          color: theme.colorScheme.onSurfaceVariant,
                        ),
                      )
                    : null,
              ),
            ),
          if (extra > 0)
            Positioned(
              left: showing.length * (size - overlap),
              child: CircleAvatar(
                radius: size / 2,
                backgroundColor: theme.colorScheme.surfaceContainerHighest,
                child: Text(
                  '+$extra',
                  style: TextStyle(
                    fontSize: 9,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ),
        ],
      ),
    );
  }
}

/// A bottom sheet listing the voters for a poll option.
class VotersSheet extends StatelessWidget {
  final String option;
  final List<PollVoter> voters;

  const VotersSheet({super.key, required this.option, required this.voters});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(option, style: theme.textTheme.titleMedium),
            const SizedBox(height: 4),
            Text(
              '${voters.length} vote${voters.length == 1 ? '' : 's'}',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSurfaceVariant,
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
                      backgroundColor:
                          theme.colorScheme.surfaceContainerHighest,
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
    );
  }
}
