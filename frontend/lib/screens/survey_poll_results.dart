import 'package:flutter/material.dart';
import 'package:pda/models/survey.dart';

class SurveyVoterAvatarStack extends StatelessWidget {
  final List<PollVoter> voters;

  const SurveyVoterAvatarStack({super.key, required this.voters});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    const size = 20.0;
    const overlap = 7.0;
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
                          fontSize: 9,
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
                    fontSize: 8,
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

class SurveyPollOptionResult extends StatelessWidget {
  final String label;
  final int count;
  final int total;
  final bool isWinner;

  const SurveyPollOptionResult({
    super.key,
    required this.label,
    required this.count,
    required this.total,
    required this.isWinner,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fraction = total > 0 ? count / total : 0.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: isWinner
              ? theme.colorScheme.primaryContainer.withValues(alpha: 0.6)
              : theme.colorScheme.surfaceContainerHighest.withValues(
                  alpha: 0.4,
                ),
          borderRadius: BorderRadius.circular(8),
          border: isWinner
              ? Border.all(
                  color: theme.colorScheme.primary.withValues(alpha: 0.4),
                )
              : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontWeight: isWinner
                          ? FontWeight.w600
                          : FontWeight.normal,
                    ),
                  ),
                ),
                if (isWinner)
                  Icon(
                    Icons.check_circle_rounded,
                    size: 16,
                    color: theme.colorScheme.primary,
                  ),
                const SizedBox(width: 4),
                Text(
                  '$count vote${count == 1 ? '' : 's'}',
                  style: TextStyle(
                    fontSize: 13,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: fraction,
                minHeight: 6,
                backgroundColor: theme.colorScheme.outline.withValues(
                  alpha: 0.15,
                ),
                color: isWinner
                    ? theme.colorScheme.primary
                    : theme.colorScheme.secondary,
              ),
            ),
          ],
        ),
      ),
    );
  }
}
