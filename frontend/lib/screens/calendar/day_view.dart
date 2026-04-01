import 'package:flutter/material.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/config/constants.dart';

class DayView extends StatefulWidget {
  final List<Event> events;
  final DateTime selectedDate;
  final ValueChanged<DateTime> onDateChanged;

  const DayView({
    super.key,
    required this.events,
    required this.selectedDate,
    required this.onDateChanged,
  });

  @override
  State<DayView> createState() => _DayViewState();
}

class _DayViewState extends State<DayView> {
  late DateTime _selectedDay;

  @override
  void initState() {
    super.initState();
    _selectedDay = DateTime(
      widget.selectedDate.year,
      widget.selectedDate.month,
      widget.selectedDate.day,
    );
  }

  @override
  void didUpdateWidget(DayView oldWidget) {
    super.didUpdateWidget(oldWidget);
    final d = widget.selectedDate;
    final normalized = DateTime(d.year, d.month, d.day);
    if (normalized != _selectedDay) {
      setState(() => _selectedDay = normalized);
    }
  }

  void _goToPrevDay() {
    final newDay = _selectedDay.subtract(const Duration(days: 1));
    setState(() => _selectedDay = newDay);
    widget.onDateChanged(newDay);
  }

  void _goToNextDay() {
    final newDay = _selectedDay.add(const Duration(days: 1));
    setState(() => _selectedDay = newDay);
    widget.onDateChanged(newDay);
  }

  List<Event> _eventsForSelectedDay() {
    final dayStart = DateTime(
      _selectedDay.year,
      _selectedDay.month,
      _selectedDay.day,
    );
    final dayEnd = dayStart.add(const Duration(days: 1));
    final results =
        widget.events.where((e) {
          final start = e.startDatetime.toLocal();
          final end =
              e.endDatetime?.toLocal() ?? start.add(const Duration(minutes: 1));
          return start.isBefore(dayEnd) && end.isAfter(dayStart);
        }).toList();
    results.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));
    return results;
  }

  @override
  Widget build(BuildContext context) {
    final events = _eventsForSelectedDay();

    return GestureDetector(
      behavior: HitTestBehavior.opaque,
      onHorizontalDragEnd: (details) {
        if ((details.primaryVelocity ?? 0) > 0) {
          _goToPrevDay();
        } else if ((details.primaryVelocity ?? 0) < 0) {
          _goToNextDay();
        }
      },
      child: Column(
        children: [
          _DayHeader(
            selectedDay: _selectedDay,
            onPrev: _goToPrevDay,
            onNext: _goToNextDay,
          ),
          const Divider(height: 1),
          Expanded(child: _buildBody(context, events)),
        ],
      ),
    );
  }

  Widget _buildBody(BuildContext context, List<Event> events) {
    if (events.isEmpty) {
      return _EmptyDayState();
    }

    return ListView.builder(
      padding: const EdgeInsets.all(12),
      itemCount: events.length,
      itemBuilder: (context, index) {
        return _DayEventCard(event: events[index]);
      },
    );
  }
}

class _DayHeader extends StatelessWidget {
  final DateTime selectedDay;
  final VoidCallback onPrev;
  final VoidCallback onNext;

  const _DayHeader({
    required this.selectedDay,
    required this.onPrev,
    required this.onNext,
  });

  @override
  Widget build(BuildContext context) {
    final label =
        DateFormat('EEEE, MMMM d, y').format(selectedDay).toLowerCase();
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            tooltip: 'previous day',
            onPressed: onPrev,
          ),
          Expanded(
            child: Text(
              label,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.titleMedium,
            ),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            tooltip: 'next day',
            onPressed: onNext,
          ),
        ],
      ),
    );
  }
}

class _EmptyDayState extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(
            Icons.event_note_outlined,
            size: 48,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
          ),
          const SizedBox(height: 12),
          Text(
            'nothing today 🌿',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
        ],
      ),
    );
  }
}

String _buildTimeRange(Event event, DateFormat dateFmt) {
  final start = event.startDatetime.toLocal();
  if (event.endDatetime == null) {
    return formatTime(start);
  }
  final end = event.endDatetime!.toLocal();
  final isSameDay =
      start.year == end.year &&
      start.month == end.month &&
      start.day == end.day;
  if (isSameDay) {
    return '${formatTime(start)} \u2013 ${formatTime(end)}';
  }
  return '${dateFmt.format(start).toLowerCase()} ${formatTime(start)} \u2013 ${dateFmt.format(end).toLowerCase()} ${formatTime(end)}';
}

class _DayEventCard extends StatelessWidget {
  final Event event;

  const _DayEventCard({required this.event});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colors = eventColors(event.id);
    final bgColor = colors.$1;
    final fgColor = colors.$2;
    final dateFmt = DateFormat('MMM d');
    final timeRange = _buildTimeRange(event, dateFmt);

    return Semantics(
      button: true,
      label: event.title,
      excludeSemantics: true,
      child: InkWell(
        onTap: () => showEventDetail(context, event),
        splashColor: Colors.transparent,
        highlightColor: Colors.transparent,
        borderRadius: BorderRadius.circular(8),
        child: Container(
          margin: const EdgeInsets.only(bottom: 10),
          decoration: BoxDecoration(
            color: bgColor,
            borderRadius: BorderRadius.circular(8),
            boxShadow: [
              BoxShadow(
                color: theme.shadowColor.withValues(alpha: 0.08),
                blurRadius: 4,
                offset: const Offset(0, 2),
              ),
            ],
          ),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  Flexible(
                    child: Text(
                      event.title,
                      style: TextStyle(
                        color: fgColor,
                        fontWeight: FontWeight.bold,
                        fontSize: 15,
                      ),
                    ),
                  ),
                  if (event.visibility == PageVisibility.membersOnly) ...[
                    const SizedBox(width: 6),
                    Icon(
                      Icons.lock_outline,
                      size: 14,
                      color: fgColor.withValues(alpha: 0.7),
                    ),
                  ],
                  if (event.eventType == EventType.official) ...[
                    const SizedBox(width: 6),
                    Container(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 5,
                        vertical: 1,
                      ),
                      decoration: BoxDecoration(
                        color: fgColor.withValues(alpha: 0.15),
                        borderRadius: BorderRadius.circular(4),
                      ),
                      child: Text(
                        'official',
                        style: TextStyle(
                          fontSize: 11,
                          fontWeight: FontWeight.w600,
                          color: fgColor,
                        ),
                      ),
                    ),
                  ],
                ],
              ),
              const SizedBox(height: 4),
              Text(timeRange, style: TextStyle(color: fgColor, fontSize: 13)),
              if (event.location.isNotEmpty) ...[
                const SizedBox(height: 2),
                Row(
                  children: [
                    Icon(Icons.place_outlined, size: 13, color: fgColor),
                    const SizedBox(width: 3),
                    Expanded(
                      child: Text(
                        event.location,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: fgColor, fontSize: 12),
                      ),
                    ),
                  ],
                ),
              ],
              if (event.description.isNotEmpty) ...[
                const SizedBox(height: 4),
                Text(
                  event.description,
                  maxLines: 2,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(color: fgColor, fontSize: 12),
                ),
              ],
            ],
          ),
        ),
      ),
    );
  }
}
