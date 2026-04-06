import 'package:flutter/material.dart';

/// Navigation row shared by month, week, and day views.
///
/// Renders: [📅 today] ← [centered label] →
class CalendarNavRow extends StatelessWidget {
  final String label;
  final VoidCallback onPrev;
  final VoidCallback onNext;
  final VoidCallback onToday;
  final String prevTooltip;
  final String nextTooltip;

  const CalendarNavRow({
    super.key,
    required this.label,
    required this.onPrev,
    required this.onNext,
    required this.onToday,
    this.prevTooltip = 'previous',
    this.nextTooltip = 'next',
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 4),
      child: Stack(
        alignment: Alignment.center,
        children: [
          // Today icon pinned to the left
          Align(
            alignment: Alignment.centerLeft,
            child: _TodayIconButton(onPressed: onToday),
          ),
          // Arrows + label as a tight centered unit
          Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              IconButton(
                icon: const Icon(Icons.chevron_left),
                onPressed: onPrev,
                tooltip: prevTooltip,
                visualDensity: VisualDensity.compact,
              ),
              Text(label, style: theme.textTheme.titleMedium),
              IconButton(
                icon: const Icon(Icons.chevron_right),
                onPressed: onNext,
                tooltip: nextTooltip,
                visualDensity: VisualDensity.compact,
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _TodayIconButton extends StatelessWidget {
  final VoidCallback onPressed;

  const _TodayIconButton({required this.onPressed});

  @override
  Widget build(BuildContext context) {
    final day = DateTime.now().day;
    final color = Theme.of(context).colorScheme.primary;
    return Tooltip(
      message: 'go to today',
      child: InkWell(
        onTap: onPressed,
        borderRadius: BorderRadius.circular(8),
        child: Semantics(
          button: true,
          label: 'go to today',
          excludeSemantics: true,
          child: Padding(
            padding: const EdgeInsets.all(6),
            child: Stack(
              alignment: Alignment.center,
              children: [
                Icon(Icons.calendar_today_outlined, size: 28, color: color),
                Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Text(
                    '$day',
                    style: TextStyle(
                      fontSize: 10,
                      fontWeight: FontWeight.w700,
                      color: color,
                      height: 1,
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
