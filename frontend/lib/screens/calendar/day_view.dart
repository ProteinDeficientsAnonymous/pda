import 'package:flutter/material.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';

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

  Future<void> _openDatePicker() async {
    final picked = await showDatePicker(
      context: context,
      initialDate: _selectedDay,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
    );
    if (picked == null) return;
    final newDay = DateTime(picked.year, picked.month, picked.day);
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
          final end = e.endDatetime.toLocal();
          return start.isBefore(dayEnd) && end.isAfter(dayStart);
        }).toList();
    results.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));
    return results;
  }

  @override
  Widget build(BuildContext context) {
    final events = _eventsForSelectedDay();

    return Column(
      children: [
        _DayHeader(
          selectedDay: _selectedDay,
          onPrev: _goToPrevDay,
          onNext: _goToNextDay,
          onTap: _openDatePicker,
        ),
        const Divider(height: 1),
        Expanded(child: _buildBody(context, events)),
      ],
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
  final VoidCallback onTap;

  const _DayHeader({
    required this.selectedDay,
    required this.onPrev,
    required this.onNext,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final label = DateFormat('EEEE, MMMM d, y').format(selectedDay);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 8, horizontal: 4),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          IconButton(
            icon: const Icon(Icons.chevron_left),
            tooltip: 'Previous day',
            onPressed: onPrev,
          ),
          GestureDetector(
            onTap: onTap,
            child: Text(label, style: Theme.of(context).textTheme.titleMedium),
          ),
          IconButton(
            icon: const Icon(Icons.chevron_right),
            tooltip: 'Next day',
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
            Icons.calendar_today_outlined,
            size: 48,
            color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
          ),
          const SizedBox(height: 12),
          Text(
            'No events today',
            style: theme.textTheme.bodyLarge?.copyWith(
              color: theme.colorScheme.onSurface.withValues(alpha: 0.4),
            ),
          ),
        ],
      ),
    );
  }
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
    final timeFmt = DateFormat('h:mm a');
    final start = event.startDatetime.toLocal();
    final end = event.endDatetime.toLocal();
    final timeRange = '${timeFmt.format(start)} \u2013 ${timeFmt.format(end)}';

    return GestureDetector(
      onTap: () => showEventDetail(context, event),
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
            Text(
              event.title,
              style: TextStyle(
                color: fgColor,
                fontWeight: FontWeight.bold,
                fontSize: 15,
              ),
            ),
            const SizedBox(height: 4),
            Text(
              timeRange,
              style: TextStyle(
                color: fgColor.withValues(alpha: 0.85),
                fontSize: 13,
              ),
            ),
            if (event.location.isNotEmpty) ...[
              const SizedBox(height: 2),
              Row(
                children: [
                  Icon(
                    Icons.place_outlined,
                    size: 13,
                    color: fgColor.withValues(alpha: 0.7),
                  ),
                  const SizedBox(width: 3),
                  Expanded(
                    child: Text(
                      event.location,
                      maxLines: 1,
                      overflow: TextOverflow.ellipsis,
                      style: TextStyle(
                        color: fgColor.withValues(alpha: 0.7),
                        fontSize: 12,
                      ),
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
                style: TextStyle(
                  color: fgColor.withValues(alpha: 0.75),
                  fontSize: 12,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}
