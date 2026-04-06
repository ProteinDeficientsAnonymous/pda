import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/placement_types.dart';
import 'package:pda/screens/calendar/week_placement_calculator.dart';
import 'package:pda/config/constants.dart';

class WideWeekGrid extends StatelessWidget {
  final List<DateTime> days;
  final List<Event> events;
  final bool Function(DateTime) isToday;
  final ValueChanged<Event> onEventTapped;
  final ValueChanged<DateTime>? onDayTapped;
  final ValueChanged<DateTime>? onDayLongPressed;

  static const double _dayLabelHeight = 52.0;
  static const double _chipHeight = 22.0;
  static const double _chipSpacing = 3.0;
  static const int _maxEventRows = 4;

  const WideWeekGrid({
    super.key,
    required this.days,
    required this.events,
    required this.isToday,
    required this.onEventTapped,
    this.onDayTapped,
    this.onDayLongPressed,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final hasAnyEvents = days.any((d) {
      final ds = DateTime(d.year, d.month, d.day);
      final de = ds.add(const Duration(days: 1));
      return events.any((e) {
        final s = e.startDatetime.toLocal();
        final en = (e.endDatetime ?? e.startDatetime).toLocal();
        return s.isBefore(de) && en.isAfter(ds);
      });
    });

    final placements = WeekPlacementCalculator(
      days: days,
      allEvents: events,
    ).calculate();

    return Padding(
      padding: const EdgeInsets.fromLTRB(12, 0, 12, 12),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Container(
          decoration: BoxDecoration(
            border: Border.all(
              color: theme.dividerColor.withValues(alpha: 0.4),
              width: 0.5,
            ),
            borderRadius: BorderRadius.circular(12),
          ),
          child: Stack(
            children: [
              LayoutBuilder(
                builder: (context, constraints) {
                  final colWidth = constraints.maxWidth / 7;
                  return Column(
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      _WideDayHeaderRow(
                        days: days,
                        isToday: isToday,
                        onDayTapped: onDayTapped,
                        onDayLongPressed: onDayLongPressed,
                        height: _dayLabelHeight,
                      ),
                      Divider(
                        height: 1,
                        color: theme.dividerColor.withValues(alpha: 0.4),
                      ),
                      Expanded(
                        child: _WideEventArea(
                          days: days,
                          placements: placements,
                          colWidth: colWidth,
                          maxEventRows: _maxEventRows,
                          chipHeight: _chipHeight,
                          chipSpacing: _chipSpacing,
                          onDayTapped: onDayTapped,
                          onDayLongPressed: onDayLongPressed,
                          onEventTapped: onEventTapped,
                        ),
                      ),
                    ],
                  );
                },
              ),
              if (!hasAnyEvents)
                Center(
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.event_note_outlined,
                        size: 40,
                        color: theme.colorScheme.onSurface.withValues(
                          alpha: 0.2,
                        ),
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'all quiet this week 🌿',
                        style: theme.textTheme.bodyMedium?.copyWith(
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
    );
  }
}

class _WideDayHeaderRow extends StatelessWidget {
  final List<DateTime> days;
  final bool Function(DateTime) isToday;
  final ValueChanged<DateTime>? onDayTapped;
  final ValueChanged<DateTime>? onDayLongPressed;
  final double height;

  const _WideDayHeaderRow({
    required this.days,
    required this.isToday,
    required this.height,
    this.onDayTapped,
    this.onDayLongPressed,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return SizedBox(
      height: height,
      child: Row(
        children: days.map((day) {
          final today = isToday(day);
          final bgColor = today
              ? theme.colorScheme.primary
              : Colors.transparent;
          final fgColor = today
              ? theme.colorScheme.onPrimary
              : theme.colorScheme.onSurface;
          return Expanded(
            child: Semantics(
              button: onDayTapped != null,
              label: DateFormat('EEEE, MMMM d').format(day),
              onLongPressHint: onDayLongPressed != null ? 'create event' : null,
              child: InkWell(
                onTap: onDayTapped != null ? () => onDayTapped!(day) : null,
                onLongPress: onDayLongPressed != null
                    ? () => onDayLongPressed!(day)
                    : null,
                borderRadius: BorderRadius.circular(8),
                child: Container(
                  decoration: BoxDecoration(
                    color: bgColor,
                    borderRadius: BorderRadius.circular(8),
                  ),
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      Text(
                        DateFormat('EEE').format(day).toLowerCase(),
                        style: TextStyle(
                          fontSize: 12,
                          fontWeight: FontWeight.w500,
                          color: fgColor,
                        ),
                      ),
                      Text(
                        '${day.day}',
                        style: TextStyle(
                          fontSize: 16,
                          fontWeight: FontWeight.w600,
                          color: fgColor,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          );
        }).toList(),
      ),
    );
  }
}

class _WideEventArea extends StatelessWidget {
  final List<DateTime> days;
  final List<SpanPlacement> placements;
  final double colWidth;
  final int maxEventRows;
  final double chipHeight;
  final double chipSpacing;
  final ValueChanged<DateTime>? onDayTapped;
  final ValueChanged<DateTime>? onDayLongPressed;
  final ValueChanged<Event> onEventTapped;

  const _WideEventArea({
    required this.days,
    required this.placements,
    required this.colWidth,
    required this.maxEventRows,
    required this.chipHeight,
    required this.chipSpacing,
    required this.onEventTapped,
    this.onDayTapped,
    this.onDayLongPressed,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Stack(
      children: [
        Row(
          children: List.generate(7, (col) {
            final overflow = placements
                .where(
                  (p) =>
                      p.row >= maxEventRows &&
                      col >= p.startCol &&
                      col <= p.endCol,
                )
                .length;
            return Expanded(
              child: Semantics(
                button: onDayTapped != null,
                label: DateFormat('EEEE, MMMM d').format(days[col]),
                onLongPressHint: onDayLongPressed != null
                    ? 'create event'
                    : null,
                child: InkWell(
                  onTap: onDayTapped != null
                      ? () => onDayTapped!(days[col])
                      : null,
                  onLongPress: onDayLongPressed != null
                      ? () => onDayLongPressed!(days[col])
                      : null,
                  child: Container(
                    decoration: BoxDecoration(
                      border: Border(
                        right: col < 6
                            ? BorderSide(
                                color: theme.dividerColor.withValues(
                                  alpha: 0.4,
                                ),
                                width: 0.5,
                              )
                            : BorderSide.none,
                      ),
                    ),
                    child: overflow > 0
                        ? Align(
                            alignment: Alignment.bottomCenter,
                            child: Padding(
                              padding: const EdgeInsets.only(bottom: 4),
                              child: Text(
                                '$overflow more',
                                style: TextStyle(
                                  fontSize: 11,
                                  fontWeight: FontWeight.w600,
                                  color: theme.colorScheme.primary,
                                ),
                              ),
                            ),
                          )
                        : null,
                  ),
                ),
              ),
            );
          }),
        ),
        Padding(
          padding: const EdgeInsets.only(top: 6),
          child: Stack(
            children: placements
                .where((p) => p.row < maxEventRows)
                .map(
                  (p) => _WideEventChip(
                    placement: p,
                    colWidth: colWidth,
                    chipHeight: chipHeight,
                    chipSpacing: chipSpacing,
                    days: days,
                    onEventTapped: onEventTapped,
                  ),
                )
                .toList(),
          ),
        ),
      ],
    );
  }
}

class _WideEventChip extends StatelessWidget {
  final SpanPlacement placement;
  final double colWidth;
  final double chipHeight;
  final double chipSpacing;
  final List<DateTime> days;
  final ValueChanged<Event> onEventTapped;

  const _WideEventChip({
    required this.placement,
    required this.colWidth,
    required this.chipHeight,
    required this.chipSpacing,
    required this.days,
    required this.onEventTapped,
  });

  @override
  Widget build(BuildContext context) {
    final p = placement;
    final left = p.startCol * colWidth;
    final width = (p.endCol - p.startCol + 1) * colWidth;
    final top = p.row * (chipHeight + chipSpacing);
    final colors = eventColors(p.event.id);

    final continuesFromPrev =
        p.startCol == 0 &&
        p.event.startDatetime.toLocal().isBefore(
          DateTime(days[0].year, days[0].month, days[0].day),
        );
    final eEnd = (p.event.endDatetime ?? p.event.startDatetime).toLocal();
    final continuesToNext =
        p.endCol == 6 &&
        eEnd.isAfter(DateTime(days[6].year, days[6].month, days[6].day + 1));

    final isMultiDay =
        p.startCol != p.endCol || continuesFromPrev || continuesToNext;

    final eStart = p.event.startDatetime.toLocal();
    final subLabel = isMultiDay
        ? '${DateFormat('MMM d').format(eStart).toLowerCase()} \u2013 ${DateFormat('MMM d').format(eEnd).toLowerCase()}'
        : formatTime(eStart);

    return Positioned(
      left: left,
      top: top,
      width: width,
      height: chipHeight,
      child: Semantics(
        button: true,
        label: p.event.title,
        excludeSemantics: true,
        child: InkWell(
          onTap: () => onEventTapped(p.event),
          splashColor: Colors.transparent,
          highlightColor: Colors.transparent,
          child: Container(
            margin: EdgeInsets.only(
              left: continuesFromPrev ? 0 : 2,
              right: continuesToNext ? 0 : 2,
            ),
            decoration: BoxDecoration(
              color: colors.$1,
              borderRadius: BorderRadius.horizontal(
                left: continuesFromPrev
                    ? Radius.zero
                    : const Radius.circular(6),
                right: continuesToNext ? Radius.zero : const Radius.circular(6),
              ),
            ),
            padding: const EdgeInsets.symmetric(horizontal: 6),
            child: Text.rich(
              TextSpan(
                children: [
                  TextSpan(
                    text: p.event.title,
                    style: TextStyle(
                      fontSize: 12,
                      fontWeight: FontWeight.w500,
                      color: colors.$2,
                    ),
                  ),
                  if (p.event.visibility == PageVisibility.membersOnly)
                    TextSpan(
                      text: ' 🔒',
                      style: TextStyle(fontSize: 11, color: colors.$2),
                    ),
                  if (p.event.eventType == EventType.official)
                    TextSpan(
                      text: ' ✦',
                      style: TextStyle(fontSize: 11, color: colors.$2),
                    ),
                  TextSpan(
                    text: '  $subLabel',
                    style: TextStyle(fontSize: 11, color: colors.$2),
                  ),
                ],
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ),
        ),
      ),
    );
  }
}
