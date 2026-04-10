import 'package:flutter/material.dart';

/// A date+time summary row with separate tappable date and time chips.
///
/// Tapping the date chip calls [onDateTap]; tapping the time chip calls
/// [onTimeTap]. Each chip is highlighted when its corresponding expanded
/// flag is true.
class EventFormDateTimeRow extends StatelessWidget {
  final String label;
  final String date;
  final String time;
  final VoidCallback onDateTap;
  final VoidCallback onTimeTap;
  final bool isDateExpanded;
  final bool isTimeExpanded;

  const EventFormDateTimeRow({
    super.key,
    required this.label,
    required this.date,
    required this.time,
    required this.onDateTap,
    required this.onTimeTap,
    this.isDateExpanded = false,
    this.isTimeExpanded = false,
  });

  Widget _chip({
    required BuildContext context,
    required String semanticLabel,
    required VoidCallback onTap,
    required bool isActive,
    required Widget child,
  }) {
    final theme = Theme.of(context);
    final color = isActive
        ? theme.colorScheme.primaryContainer
        : theme.colorScheme.surfaceContainerHighest;
    return Semantics(
      button: true,
      label: semanticLabel,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
          decoration: BoxDecoration(
            color: color,
            borderRadius: BorderRadius.circular(8),
          ),
          child: child,
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final textStyle = theme.textTheme.bodyMedium;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: theme.textTheme.labelMedium?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 4),
        Row(
          children: [
            Flexible(
              child: _chip(
                context: context,
                semanticLabel: '$label date',
                onTap: onDateTap,
                isActive: isDateExpanded,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    const Icon(Icons.calendar_today_outlined, size: 14),
                    const SizedBox(width: 6),
                    Flexible(
                      child: Text(
                        date,
                        style: textStyle,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                  ],
                ),
              ),
            ),
            const SizedBox(width: 8),
            _chip(
              context: context,
              semanticLabel: '$label time',
              onTap: onTimeTap,
              isActive: isTimeExpanded,
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(Icons.schedule_outlined, size: 14),
                  const SizedBox(width: 6),
                  Text(time, style: textStyle),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}

class EventFormPhotoButton extends StatelessWidget {
  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;

  const EventFormPhotoButton({
    super.key,
    required this.tooltip,
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    return Tooltip(
      message: tooltip,
      child: Material(
        color: Theme.of(context).colorScheme.onSurface.withValues(alpha: 0.38),
        borderRadius: BorderRadius.circular(8),
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(8),
          child: Padding(
            padding: const EdgeInsets.all(6),
            child: Icon(
              icon,
              size: 16,
              color: Theme.of(context).colorScheme.surface,
            ),
          ),
        ),
      ),
    );
  }
}
