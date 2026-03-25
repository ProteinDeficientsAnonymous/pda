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
  late ScrollController _scrollController;

  static const double _hourHeight = 60.0;
  static const double _totalHeight = _hourHeight * 24;
  static const double _timeColumnWidth = 56.0;

  @override
  void initState() {
    super.initState();
    _selectedDay = DateTime(
      widget.selectedDate.year,
      widget.selectedDate.month,
      widget.selectedDate.day,
    );
    _scrollController = ScrollController();
    WidgetsBinding.instance.addPostFrameCallback((_) => _scrollToCurrentHour());
  }

  @override
  void dispose() {
    _scrollController.dispose();
    super.dispose();
  }

  DateTime _today() {
    final now = DateTime.now();
    return DateTime(now.year, now.month, now.day);
  }

  bool _isToday() {
    final today = _today();
    return _selectedDay.year == today.year &&
        _selectedDay.month == today.month &&
        _selectedDay.day == today.day;
  }

  void _scrollToCurrentHour() {
    if (!_scrollController.hasClients) return;
    final now = DateTime.now();
    final targetOffset = (now.hour - 1) * _hourHeight;
    final clamped = targetOffset.clamp(
      0.0,
      _scrollController.position.maxScrollExtent,
    );
    _scrollController.jumpTo(clamped);
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
    return widget.events.where((e) {
      final start = e.startDatetime.toLocal();
      return start.year == _selectedDay.year &&
          start.month == _selectedDay.month &&
          start.day == _selectedDay.day;
    }).toList();
  }

  double _topForTime(DateTime time) {
    final local = time.toLocal();
    return (local.hour + local.minute / 60.0) * _hourHeight;
  }

  double _heightForEvent(Event event) {
    final start = event.startDatetime.toLocal();
    final end = event.endDatetime.toLocal();
    final durationMinutes = end.difference(start).inMinutes.toDouble();
    return durationMinutes.clamp(30.0, double.infinity);
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      children: [
        _DayHeader(
          selectedDay: _selectedDay,
          onPrev: _goToPrevDay,
          onNext: _goToNextDay,
          onTap: _openDatePicker,
        ),
        Expanded(
          child: Stack(
            children: [
              SingleChildScrollView(
                controller: _scrollController,
                child: SizedBox(
                  height: _totalHeight,
                  child: Row(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      const _TimeLabelsColumn(
                        hourHeight: _hourHeight,
                        columnWidth: _timeColumnWidth,
                      ),
                      Expanded(
                        child: _EventArea(
                          events: _eventsForSelectedDay(),
                          totalHeight: _totalHeight,
                          hourHeight: _hourHeight,
                          showCurrentTimeLine: _isToday(),
                          topForTime: _topForTime,
                          heightForEvent: _heightForEvent,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              if (_eventsForSelectedDay().isEmpty)
                Positioned.fill(
                  child: IgnorePointer(
                    child: Center(
                      child: Column(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.calendar_today_outlined,
                            size: 48,
                            color: Theme.of(
                              context,
                            ).colorScheme.onSurface.withValues(alpha: 0.3),
                          ),
                          const SizedBox(height: 12),
                          Text(
                            'No events today',
                            style: Theme.of(
                              context,
                            ).textTheme.bodyLarge?.copyWith(
                              color: Theme.of(
                                context,
                              ).colorScheme.onSurface.withValues(alpha: 0.4),
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
            ],
          ),
        ),
      ],
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

class _TimeLabelsColumn extends StatelessWidget {
  final double hourHeight;
  final double columnWidth;

  const _TimeLabelsColumn({
    required this.hourHeight,
    required this.columnWidth,
  });

  String _labelForHour(int hour) {
    if (hour == 0) return '12am';
    if (hour < 12) return '${hour}am';
    if (hour == 12) return '12pm';
    return '${hour - 12}pm';
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: columnWidth,
      child: Stack(
        children: List.generate(24, (hour) {
          return Positioned(
            top: hour * hourHeight - 8,
            left: 0,
            right: 0,
            child: Align(
              alignment: Alignment.centerRight,
              child: Padding(
                padding: const EdgeInsets.only(right: 6),
                child: Text(
                  _labelForHour(hour),
                  style: Theme.of(context).textTheme.labelSmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
              ),
            ),
          );
        }),
      ),
    );
  }
}

class _EventArea extends StatelessWidget {
  final List<Event> events;
  final double totalHeight;
  final double hourHeight;
  final bool showCurrentTimeLine;
  final double Function(DateTime) topForTime;
  final double Function(Event) heightForEvent;

  const _EventArea({
    required this.events,
    required this.totalHeight,
    required this.hourHeight,
    required this.showCurrentTimeLine,
    required this.topForTime,
    required this.heightForEvent,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      children: [
        _HourDividers(totalHeight: totalHeight, hourHeight: hourHeight),
        ..._buildEventBlocks(context),
        if (showCurrentTimeLine) _CurrentTimeLine(topForTime: topForTime),
      ],
    );
  }

  List<Widget> _buildEventBlocks(BuildContext context) {
    return events.map((event) {
      final top = topForTime(event.startDatetime);
      final height = heightForEvent(event);
      return Positioned(
        top: top,
        left: 2,
        right: 4,
        height: height,
        child: _EventBlock(event: event),
      );
    }).toList();
  }
}

class _HourDividers extends StatelessWidget {
  final double totalHeight;
  final double hourHeight;

  const _HourDividers({required this.totalHeight, required this.hourHeight});

  @override
  Widget build(BuildContext context) {
    final dividerColor = Theme.of(
      context,
    ).colorScheme.outlineVariant.withValues(alpha: 0.5);
    return Stack(
      children: List.generate(24, (hour) {
        return Positioned(
          top: hour * hourHeight,
          left: 0,
          right: 0,
          child: Divider(height: 1, color: dividerColor),
        );
      }),
    );
  }
}

class _CurrentTimeLine extends StatelessWidget {
  final double Function(DateTime) topForTime;

  const _CurrentTimeLine({required this.topForTime});

  @override
  Widget build(BuildContext context) {
    final now = DateTime.now();
    final top = topForTime(now);
    return Positioned(
      top: top,
      left: 0,
      right: 0,
      child: Row(
        children: [
          Container(
            width: 8,
            height: 8,
            decoration: const BoxDecoration(
              color: Colors.red,
              shape: BoxShape.circle,
            ),
          ),
          Expanded(child: Container(height: 1.5, color: Colors.red)),
        ],
      ),
    );
  }
}

class _EventBlock extends StatelessWidget {
  final Event event;

  const _EventBlock({required this.event});

  @override
  Widget build(BuildContext context) {
    final colors = eventColors(event.id);
    final bgColor = colors.$1;
    final fgColor = colors.$2;
    final start = event.startDatetime.toLocal();
    final end = event.endDatetime.toLocal();
    final timeFmt = DateFormat('h:mm a');
    final timeLabel = '${timeFmt.format(start)} – ${timeFmt.format(end)}';

    return GestureDetector(
      onTap: () => showEventDetail(context, event),
      child: Container(
        margin: const EdgeInsets.symmetric(vertical: 1),
        decoration: BoxDecoration(
          color: bgColor,
          borderRadius: BorderRadius.circular(4),
        ),
        padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 3),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              event.title,
              style: TextStyle(
                color: fgColor,
                fontWeight: FontWeight.w600,
                fontSize: 12,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
            Text(
              timeLabel,
              style: TextStyle(
                color: fgColor.withValues(alpha: 0.8),
                fontSize: 11,
              ),
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
            ),
          ],
        ),
      ),
    );
  }
}
