import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/utils/time_format.dart';

class EventListView extends StatefulWidget {
  final List<Event> events;

  const EventListView({super.key, required this.events});

  @override
  State<EventListView> createState() => _EventListViewState();
}

class _EventListViewState extends State<EventListView> {
  final _searchController = TextEditingController();
  String _query = '';
  String? _typeFilter;
  bool _showUpcoming = true;
  bool _sortAscending = true;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Event> _filterAndSort(List<Event> events) {
    var result = events;

    if (_query.isNotEmpty) {
      final q = _query.toLowerCase();
      result = result.where((e) => e.title.toLowerCase().contains(q)).toList();
    }

    if (_typeFilter != null) {
      result = result.where((e) => e.eventType == _typeFilter).toList();
    }

    final now = DateTime.now();
    if (_showUpcoming) {
      result =
          result
              .where((e) => (e.endDatetime ?? e.startDatetime).isAfter(now))
              .toList();
    } else {
      result =
          result
              .where((e) => !(e.endDatetime ?? e.startDatetime).isAfter(now))
              .toList();
    }

    result = List.of(result);
    if (_sortAscending) {
      result.sort((a, b) => a.startDatetime.compareTo(b.startDatetime));
    } else {
      result.sort((a, b) => b.startDatetime.compareTo(a.startDatetime));
    }

    return result;
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filterAndSort(widget.events);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 12, 16, 4),
          child: TextField(
            controller: _searchController,
            decoration: InputDecoration(
              hintText: 'search events...',
              prefixIcon: const Icon(Icons.search, size: 20),
              isDense: true,
              border: OutlineInputBorder(
                borderRadius: BorderRadius.circular(8),
              ),
              contentPadding: const EdgeInsets.symmetric(
                horizontal: 12,
                vertical: 10,
              ),
              suffixIcon:
                  _query.isNotEmpty
                      ? IconButton(
                        icon: const Icon(Icons.close, size: 18),
                        tooltip: 'clear search',
                        onPressed: () {
                          _searchController.clear();
                          setState(() => _query = '');
                        },
                      )
                      : null,
            ),
            onChanged: (v) => setState(() => _query = v),
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
          child: Wrap(
            spacing: 8,
            runSpacing: 4,
            crossAxisAlignment: WrapCrossAlignment.center,
            children: [
              SegmentedButton<String?>(
                segments: const [
                  ButtonSegment(value: null, label: Text('all')),
                  ButtonSegment(
                    value: EventType.official,
                    label: Text('official'),
                  ),
                  ButtonSegment(
                    value: EventType.community,
                    label: Text('community'),
                  ),
                ],
                selected: {_typeFilter},
                onSelectionChanged:
                    (s) => setState(() => _typeFilter = s.first),
                showSelectedIcon: false,
                style: const ButtonStyle(visualDensity: VisualDensity.compact),
              ),
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(value: true, label: Text('upcoming')),
                  ButtonSegment(value: false, label: Text('past')),
                ],
                selected: {_showUpcoming},
                onSelectionChanged:
                    (s) => setState(() => _showUpcoming = s.first),
                showSelectedIcon: false,
                style: const ButtonStyle(visualDensity: VisualDensity.compact),
              ),
              IconButton(
                icon: Icon(
                  _sortAscending ? Icons.arrow_upward : Icons.arrow_downward,
                ),
                tooltip:
                    _sortAscending ? 'sort newest first' : 'sort oldest first',
                onPressed:
                    () => setState(() => _sortAscending = !_sortAscending),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
          child: Text(
            filtered.isEmpty
                ? 'no events'
                : '${filtered.length} event${filtered.length == 1 ? '' : 's'}',
            style: Theme.of(context).textTheme.bodySmall?.copyWith(
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
        Expanded(
          child:
              filtered.isEmpty
                  ? _EmptyState(query: _query, showUpcoming: _showUpcoming)
                  : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(16, 4, 16, 24),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 10),
                    itemBuilder:
                        (context, index) =>
                            _EventListRow(event: filtered[index]),
                  ),
        ),
      ],
    );
  }
}

class _EmptyState extends StatelessWidget {
  final String query;
  final bool showUpcoming;

  const _EmptyState({required this.query, required this.showUpcoming});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final message =
        query.isNotEmpty
            ? 'no matches for "$query"'
            : showUpcoming
            ? 'nothing upcoming 🌿'
            : 'no past events';
    return Center(
      child: Padding(
        padding: const EdgeInsets.all(32),
        child: Text(
          message,
          style: theme.textTheme.bodyLarge?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
          textAlign: TextAlign.center,
        ),
      ),
    );
  }
}

class _EventListRow extends StatelessWidget {
  final Event event;

  const _EventListRow({required this.event});

  @override
  Widget build(BuildContext context) {
    final (bg, fg) = eventColors(event.id);
    final dateFmt = DateFormat('EEE, MMM d');
    final start = event.startDatetime.toLocal();
    final timeStr =
        event.endDatetime == null
            ? '${dateFmt.format(start).toLowerCase()} · ${formatTime(start)}'
            : '${dateFmt.format(start).toLowerCase()} · ${formatTime(start)} — ${formatTime(event.endDatetime!.toLocal())}';

    final hostNames = <String>[
      if (event.createdByName != null) event.createdByName!,
      ...event.coHostNames,
    ];

    return Semantics(
      button: true,
      label: event.title,
      excludeSemantics: true,
      child: Card(
        elevation: 0,
        clipBehavior: Clip.antiAlias,
        color: bg,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
        child: InkWell(
          onTap: () => context.push('/events/${event.id}'),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Flexible(
                      child: Text(
                        event.title,
                        style: Theme.of(
                          context,
                        ).textTheme.titleMedium?.copyWith(color: fg),
                      ),
                    ),
                    if (event.eventType == EventType.official) ...[
                      const SizedBox(width: 8),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 6,
                          vertical: 2,
                        ),
                        decoration: BoxDecoration(
                          color: fg.withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(4),
                        ),
                        child: Text(
                          'official',
                          style: TextStyle(
                            fontSize: 10,
                            fontWeight: FontWeight.w600,
                            color: fg,
                          ),
                        ),
                      ),
                    ],
                    if (event.visibility == PageVisibility.membersOnly) ...[
                      const SizedBox(width: 6),
                      Icon(Icons.lock_outline, size: 14, color: fg),
                    ],
                  ],
                ),
                const SizedBox(height: 4),
                Row(
                  children: [
                    Icon(Icons.schedule_outlined, size: 14, color: fg),
                    const SizedBox(width: 4),
                    Flexible(
                      child: Text(
                        timeStr,
                        style: TextStyle(fontSize: 13, color: fg),
                      ),
                    ),
                  ],
                ),
                if (event.location.isNotEmpty) ...[
                  const SizedBox(height: 2),
                  Row(
                    children: [
                      Icon(Icons.location_on_outlined, size: 14, color: fg),
                      const SizedBox(width: 4),
                      Flexible(
                        child: Text(
                          event.location,
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 13, color: fg),
                        ),
                      ),
                    ],
                  ),
                ],
                if (hostNames.isNotEmpty) ...[
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      Icon(Icons.person_pin_outlined, size: 14, color: fg),
                      const SizedBox(width: 4),
                      Expanded(
                        child: Text(
                          hostNames.join(', '),
                          maxLines: 1,
                          overflow: TextOverflow.ellipsis,
                          style: TextStyle(fontSize: 13, color: fg),
                        ),
                      ),
                    ],
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
