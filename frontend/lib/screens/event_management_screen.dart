import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/config/constants.dart';

class EventManagementScreen extends ConsumerWidget {
  final bool myEventsOnly;

  const EventManagementScreen({super.key, this.myEventsOnly = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(eventsProvider);
    final user = ref.watch(authProvider).valueOrNull;

    return AppScaffold(
      child: eventsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (e, _) => const Center(
              child: Text('couldn\'t load events — try refreshing'),
            ),
        data: (events) {
          final filtered =
              myEventsOnly && user != null
                  ? events
                      .where(
                        (e) =>
                            e.createdById == user.id ||
                            e.coHostIds.contains(user.id),
                      )
                      .toList()
                  : events;
          return _EventManagementBody(
            events: filtered,
            myEventsOnly: myEventsOnly,
          );
        },
      ),
    );
  }
}

enum _SortField { date, title, type }

class _EventManagementBody extends ConsumerStatefulWidget {
  final List<Event> events;
  final bool myEventsOnly;

  const _EventManagementBody({
    required this.events,
    required this.myEventsOnly,
  });

  @override
  ConsumerState<_EventManagementBody> createState() =>
      _EventManagementBodyState();
}

class _EventManagementBodyState extends ConsumerState<_EventManagementBody> {
  final _searchController = TextEditingController();
  String _query = '';
  _SortField _sort = _SortField.date;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Event> _filterAndSort(List<Event> events) {
    var filtered = events;
    if (_query.isNotEmpty) {
      final q = _query.toLowerCase();
      filtered =
          events.where((e) => e.title.toLowerCase().contains(q)).toList();
    }
    filtered = List.of(filtered);
    filtered.sort((a, b) {
      return switch (_sort) {
        _SortField.date => b.startDatetime.compareTo(a.startDatetime),
        _SortField.title => a.title.toLowerCase().compareTo(
          b.title.toLowerCase(),
        ),
        _SortField.type => a.eventType.compareTo(b.eventType),
      };
    });
    return filtered;
  }

  Future<void> _showCreateDialog() async {
    final result = await showDialog<EventFormResult>(
      context: context,
      builder: (_) => const EventFormDialog(),
    );
    if (result == null) return;
    try {
      final api = ref.read(apiClientProvider);
      final response = await api.post(
        '/api/community/events/',
        data: result.data,
      );
      final eventId = (response.data as Map<String, dynamic>)['id'] as String;
      if (result.photo != null) {
        await uploadEventPhoto(ref, eventId, result.photo!);
      }
      ref.invalidate(eventsProvider);
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filterAndSort(widget.events);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 12),
          child: Row(
            children: [
              Expanded(
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
              const SizedBox(width: 8),
              SegmentedButton<_SortField>(
                segments: const [
                  ButtonSegment(value: _SortField.date, label: Text('date')),
                  ButtonSegment(value: _SortField.title, label: Text('title')),
                  ButtonSegment(value: _SortField.type, label: Text('type')),
                ],
                selected: {_sort},
                onSelectionChanged: (s) => setState(() => _sort = s.first),
                style: ButtonStyle(
                  visualDensity: VisualDensity.compact,
                  textStyle: WidgetStatePropertyAll(
                    Theme.of(context).textTheme.labelSmall,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: _showCreateDialog,
                icon: const Icon(Icons.add_circle_outline),
                label: const Text('new event'),
              ),
            ],
          ),
        ),
        Expanded(
          child:
              filtered.isEmpty
                  ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(32),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.calendar_today_outlined,
                            size: 64,
                            color: Colors.grey,
                          ),
                          const SizedBox(height: 16),
                          Text(
                            _query.isNotEmpty
                                ? 'no matches for "$_query"'
                                : 'no events yet',
                            style: const TextStyle(
                              fontSize: 18,
                              color: Colors.grey,
                            ),
                          ),
                          if (_query.isEmpty) ...[
                            const SizedBox(height: 8),
                            Text(
                              widget.myEventsOnly
                                  ? "you haven't created or co-hosted any events yet"
                                  : 'create one to get started',
                              style: const TextStyle(color: Colors.grey),
                            ),
                          ],
                        ],
                      ),
                    ),
                  )
                  : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                    itemCount: filtered.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder:
                        (context, index) =>
                            _EventManagementRow(event: filtered[index]),
                  ),
        ),
      ],
    );
  }
}

class _HostsLine extends StatelessWidget {
  final Event event;
  final Color? color;

  const _HostsLine({required this.event, this.color});

  @override
  Widget build(BuildContext context) {
    final names = <String>[];
    if (event.createdByName != null) names.add(event.createdByName!);
    names.addAll(event.coHostNames);

    if (names.isEmpty) return const SizedBox.shrink();

    final c = color ?? Colors.grey;

    return Row(
      children: [
        Icon(Icons.person_pin_outlined, size: 14, color: c),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            names.join(', '),
            style: TextStyle(fontSize: 13, color: c),
            overflow: TextOverflow.ellipsis,
          ),
        ),
      ],
    );
  }
}

class _EventManagementRow extends ConsumerWidget {
  final Event event;

  const _EventManagementRow({required this.event});

  Future<void> _showEditDialog(BuildContext context, WidgetRef ref) async {
    final result = await showDialog<EventFormResult>(
      context: context,
      builder: (_) => EventFormDialog(event: event),
    );
    if (result == null) return;
    try {
      final api = ref.read(apiClientProvider);
      await api.patch('/api/community/events/${event.id}/', data: result.data);
      if (result.photo != null) {
        await uploadEventPhoto(ref, event.id, result.photo!);
      } else if (result.removePhoto) {
        await deleteEventPhoto(ref, event.id);
      }
      ref.invalidate(eventsProvider);
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder:
          (_) => AlertDialog(
            title: const Text('Delete event'),
            content: Text('Delete "${event.title}"? This cannot be undone.'),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                style: FilledButton.styleFrom(
                  backgroundColor: Theme.of(context).colorScheme.error,
                ),
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Delete'),
              ),
            ],
          ),
    );

    if (confirmed != true) return;

    try {
      final api = ref.read(apiClientProvider);
      await api.delete('/api/community/events/${event.id}/');
      ref.invalidate(eventsProvider);
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dateFmt = DateFormat('EEE, MMM d');

    final (bg, fg) = eventColors(event.id);

    return Card(
      elevation: 0,
      clipBehavior: Clip.antiAlias,
      color: bg,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      child: InkWell(
        onTap: () => context.push('/events/${event.id}'),
        child: Padding(
          padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
          child: Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
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
                              color: Theme.of(
                                context,
                              ).colorScheme.primary.withValues(alpha: 0.15),
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              'official',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: Theme.of(context).colorScheme.primary,
                              ),
                            ),
                          ),
                        ],
                      ],
                    ),
                    const SizedBox(height: 4),
                    Row(
                      children: [
                        Icon(
                          Icons.schedule_outlined,
                          size: 14,
                          color: fg.withAlpha(153),
                        ),
                        const SizedBox(width: 4),
                        Flexible(
                          child: Text(
                            event.endDatetime == null
                                ? '${dateFmt.format(event.startDatetime.toLocal()).toLowerCase()} · ${formatTime(event.startDatetime.toLocal())}'
                                : '${dateFmt.format(event.startDatetime.toLocal()).toLowerCase()} · ${formatTime(event.startDatetime.toLocal())} — '
                                    '${formatTime(event.endDatetime!.toLocal())}',
                            style: TextStyle(
                              fontSize: 13,
                              color: fg.withAlpha(153),
                            ),
                          ),
                        ),
                      ],
                    ),
                    if (event.location.isNotEmpty) ...[
                      const SizedBox(height: 2),
                      Row(
                        children: [
                          Icon(
                            Icons.location_on_outlined,
                            size: 14,
                            color: fg.withAlpha(153),
                          ),
                          const SizedBox(width: 4),
                          Flexible(
                            child: Text(
                              event.location,
                              style: TextStyle(
                                fontSize: 13,
                                color: fg.withAlpha(153),
                              ),
                            ),
                          ),
                        ],
                      ),
                    ],
                    const SizedBox(height: 4),
                    _HostsLine(event: event, color: fg.withAlpha(153)),
                  ],
                ),
              ),
              const SizedBox(width: 8),
              IconButton(
                tooltip: 'Edit',
                icon: Icon(Icons.edit_outlined, color: fg.withAlpha(178)),
                onPressed: () => _showEditDialog(context, ref),
              ),
              IconButton(
                tooltip: 'Delete',
                icon: Icon(
                  Icons.delete_outline,
                  color: Theme.of(context).colorScheme.error,
                ),
                onPressed: () => _confirmDelete(context, ref),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
