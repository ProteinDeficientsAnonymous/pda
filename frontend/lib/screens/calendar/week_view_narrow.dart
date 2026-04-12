import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/placement_types.dart';
import 'package:pda/config/constants.dart';

class NarrowWeekGrid extends StatelessWidget {
  final List<DateTime> days;
  final List<Event> events;
  final bool Function(DateTime) isToday;
  final ValueChanged<Event> onEventTapped;
  final ValueChanged<DateTime>? onDayTapped;
  final ValueChanged<DateTime>? onDayLongPressed;

  static int maxVisibleForHeight(double height) {
    if (height.isInfinite) return 3;
    // 7 equal rows; each chip is 22px + 2px vertical padding = 24px.
    // Reserve ~20px for the "+N more" overflow label when present.
    final rowHeight = height / 7;
    final availableForChips = rowHeight - 20;
    return (availableForChips / 24).floor().clamp(1, 10);
  }

  const NarrowWeekGrid({
    super.key,
    required this.days,
    required this.events,
    required this.isToday,
    required this.onEventTapped,
    this.onDayTapped,
    this.onDayLongPressed,
  });

  List<Event> _eventsForDay(DateTime day) {
    final results = events.where((e) => dayContains(day, e)).toList();
    results.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));
    return results;
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: LayoutBuilder(
        builder: (context, constraints) {
          final maxVisible = maxVisibleForHeight(constraints.maxHeight);
          return ClipRRect(
            borderRadius: BorderRadius.circular(12),
            child: Container(
              decoration: BoxDecoration(
                border: Border.all(
                  color: theme.dividerColor.withValues(alpha: 0.4),
                  width: 0.5,
                ),
                borderRadius: BorderRadius.circular(12),
              ),
              child: Column(
                children: List.generate(7, (i) {
                  final day = days[i];
                  final dayEvents = _eventsForDay(day);
                  return Expanded(
                    child: NarrowDayRow(
                      day: day,
                      events: dayEvents,
                      isToday: isToday(day),
                      isLast: i == 6,
                      maxVisible: maxVisible,
                      onDayTapped: onDayTapped,
                      onDayLongPressed: onDayLongPressed,
                      onEventTapped: onEventTapped,
                    ),
                  );
                }),
              ),
            ),
          );
        },
      ),
    );
  }
}

class NarrowDayRow extends StatelessWidget {
  final DateTime day;
  final List<Event> events;
  final bool isToday;
  final bool isLast;
  final int maxVisible;
  final ValueChanged<DateTime>? onDayTapped;
  final ValueChanged<DateTime>? onDayLongPressed;
  final ValueChanged<Event> onEventTapped;

  const NarrowDayRow({
    super.key,
    required this.day,
    required this.events,
    required this.isToday,
    required this.isLast,
    required this.maxVisible,
    required this.onDayTapped,
    this.onDayLongPressed,
    required this.onEventTapped,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final visible = events.take(maxVisible).toList();
    final overflow = events.length - maxVisible;

    return Semantics(
      button: onDayTapped != null,
      label: DateFormat('EEEE, MMMM d').format(day),
      onLongPressHint: onDayLongPressed != null ? 'create event' : null,
      child: InkWell(
        onTap: onDayTapped != null ? () => onDayTapped!(day) : null,
        onLongPress: onDayLongPressed != null
            ? () => onDayLongPressed!(day)
            : null,
        child: Container(
          decoration: BoxDecoration(
            border: Border(
              bottom: isLast
                  ? BorderSide.none
                  : BorderSide(
                      color: theme.dividerColor.withValues(alpha: 0.4),
                      width: 0.5,
                    ),
            ),
          ),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              // Day label
              SizedBox(
                width: 56,
                child: Center(
                  child: NarrowDayLabel(day: day, isToday: isToday),
                ),
              ),
              // Divider
              Container(
                width: 0.5,
                color: theme.dividerColor.withValues(alpha: 0.4),
              ),
              // Events
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: 4,
                    vertical: 2,
                  ),
                  child: events.isEmpty
                      ? const SizedBox.shrink()
                      : Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          crossAxisAlignment: CrossAxisAlignment.stretch,
                          children: [
                            ...visible.map(
                              (e) => NarrowEventChip(
                                event: e,
                                onTap: () => onEventTapped(e),
                              ),
                            ),
                            if (overflow > 0)
                              Semantics(
                                button: true,
                                label: '$overflow more events',
                                child: InkWell(
                                  onTap: onDayTapped != null
                                      ? () => onDayTapped!(day)
                                      : null,
                                  borderRadius: BorderRadius.circular(4),
                                  child: Padding(
                                    padding: const EdgeInsets.only(
                                      left: 4,
                                      top: 1,
                                    ),
                                    child: Text(
                                      '$overflow more',
                                      style: TextStyle(
                                        fontSize: 11,
                                        fontWeight: FontWeight.w600,
                                        color: theme.colorScheme.primary,
                                      ),
                                    ),
                                  ),
                                ),
                              ),
                          ],
                        ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class NarrowDayLabel extends StatelessWidget {
  final DateTime day;
  final bool isToday;

  const NarrowDayLabel({super.key, required this.day, required this.isToday});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dayName = DateFormat('EEE').format(day).toLowerCase();
    final dayNum = '${day.day}';

    if (isToday) {
      return Container(
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        decoration: BoxDecoration(
          color: theme.colorScheme.primary,
          borderRadius: BorderRadius.circular(10),
        ),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(
              dayName,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w600,
                color: theme.colorScheme.onPrimary,
              ),
            ),
            Text(
              dayNum,
              style: TextStyle(
                fontSize: 14,
                fontWeight: FontWeight.w700,
                color: theme.colorScheme.onPrimary,
              ),
            ),
          ],
        ),
      );
    }

    return Column(
      mainAxisSize: MainAxisSize.min,
      children: [
        Text(
          dayName,
          style: TextStyle(
            fontSize: 11,
            fontWeight: FontWeight.w500,
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        Text(
          dayNum,
          style: TextStyle(
            fontSize: 14,
            fontWeight: FontWeight.w600,
            color: theme.colorScheme.onSurface,
          ),
        ),
      ],
    );
  }
}

class NarrowEventChip extends StatelessWidget {
  final Event event;
  final VoidCallback onTap;

  const NarrowEventChip({super.key, required this.event, required this.onTap});

  String _buildLabel() {
    final lockSuffix = event.visibility == PageVisibility.membersOnly
        ? ' 🔒'
        : '';
    final officialSuffix = event.eventType == EventType.official ? ' ✦' : '';
    final suffix = '$lockSuffix$officialSuffix';
    final dateFmt = DateFormat('MMM d');
    final start = event.startDatetime.toLocal();
    final end = event.endDatetime?.toLocal();

    if (end == null) {
      return '${event.title}$suffix \u00b7 ${formatTime(start)}';
    }

    final sameDay =
        start.year == end.year &&
        start.month == end.month &&
        start.day == end.day;

    if (sameDay) {
      return '${event.title}$suffix \u00b7 ${formatTime(start)} \u2013 ${formatTime(end)}';
    }

    return '${event.title}$suffix \u00b7 ${dateFmt.format(start).toLowerCase()} \u2013 ${dateFmt.format(end).toLowerCase()}';
  }

  @override
  Widget build(BuildContext context) {
    final colors = eventColors(event.eventType, Theme.of(context).brightness);

    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 1),
      child: Semantics(
        button: true,
        label: event.title,
        excludeSemantics: true,
        child: InkWell(
          onTap: onTap,
          splashColor: Colors.transparent,
          highlightColor: Colors.transparent,
          borderRadius: BorderRadius.circular(4),
          child: Container(
            height: 22,
            decoration: BoxDecoration(
              color: colors.$1,
              borderRadius: BorderRadius.circular(4),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 6),
            alignment: Alignment.centerLeft,
            child: Text(
              _buildLabel(),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11,
                fontWeight: FontWeight.w500,
                color: colors.$2,
              ),
            ),
          ),
        ),
      ),
    );
  }
}
