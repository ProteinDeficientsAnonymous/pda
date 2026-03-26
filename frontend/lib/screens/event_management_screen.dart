import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/widgets/app_scaffold.dart';

class EventManagementScreen extends ConsumerWidget {
  final bool myEventsOnly;

  const EventManagementScreen({super.key, this.myEventsOnly = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(eventsProvider);
    final user = ref.watch(authProvider).valueOrNull;

    return AppScaffold(
      title: myEventsOnly ? 'My Events' : 'Manage Events',
      child: eventsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Failed to load events: $e')),
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

class _EventManagementBody extends ConsumerWidget {
  final List<Event> events;
  final bool myEventsOnly;

  const _EventManagementBody({
    required this.events,
    required this.myEventsOnly,
  });

  Future<void> _showCreateDialog(BuildContext context, WidgetRef ref) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const EventFormDialog(),
    );
    if (result == null) return;
    final api = ref.read(apiClientProvider);
    await api.post('/api/community/events/', data: result);
    ref.invalidate(eventsProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 24, 24, 12),
          child: Align(
            alignment: Alignment.centerRight,
            child: FilledButton.icon(
              onPressed: () => _showCreateDialog(context, ref),
              icon: const Icon(Icons.add),
              label: const Text('New event'),
            ),
          ),
        ),
        Expanded(
          child:
              events.isEmpty
                  ? Center(
                    child: Padding(
                      padding: const EdgeInsets.all(32),
                      child: Column(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          const Icon(
                            Icons.event_note,
                            size: 64,
                            color: Colors.grey,
                          ),
                          const SizedBox(height: 16),
                          const Text(
                            'No events yet',
                            style: TextStyle(fontSize: 18, color: Colors.grey),
                          ),
                          const SizedBox(height: 8),
                          Text(
                            myEventsOnly
                                ? "You haven't created or co-hosted any events."
                                : 'Create one to get started.',
                            style: const TextStyle(color: Colors.grey),
                          ),
                        ],
                      ),
                    ),
                  )
                  : ListView.separated(
                    padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                    itemCount: events.length,
                    separatorBuilder: (_, __) => const SizedBox(height: 12),
                    itemBuilder:
                        (context, index) =>
                            _EventManagementRow(event: events[index]),
                  ),
        ),
      ],
    );
  }
}

class _HostsLine extends StatelessWidget {
  final Event event;

  const _HostsLine({required this.event});

  @override
  Widget build(BuildContext context) {
    final names = <String>[];
    if (event.createdByName != null) names.add(event.createdByName!);
    names.addAll(event.coHostNames);

    if (names.isEmpty) return const SizedBox.shrink();

    return Row(
      children: [
        const Icon(Icons.person_outline, size: 14, color: Colors.grey),
        const SizedBox(width: 4),
        Expanded(
          child: Text(
            names.join(', '),
            style: const TextStyle(fontSize: 13, color: Colors.grey),
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
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => EventFormDialog(event: event),
    );
    if (result == null) return;
    final api = ref.read(apiClientProvider);
    await api.patch('/api/community/events/${event.id}/', data: result);
    ref.invalidate(eventsProvider);
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

    final api = ref.read(apiClientProvider);
    await api.delete('/api/community/events/${event.id}/');
    ref.invalidate(eventsProvider);
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dateFmt = DateFormat('EEE, MMM d · h:mm a');

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    event.title,
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Row(
                    children: [
                      const Icon(Icons.schedule, size: 14, color: Colors.grey),
                      const SizedBox(width: 4),
                      Text(
                        '${dateFmt.format(event.startDatetime.toLocal())} — '
                        '${DateFormat('h:mm a').format(event.endDatetime.toLocal())}',
                        style: const TextStyle(
                          fontSize: 13,
                          color: Colors.grey,
                        ),
                      ),
                    ],
                  ),
                  if (event.location.isNotEmpty) ...[
                    const SizedBox(height: 2),
                    Row(
                      children: [
                        const Icon(Icons.place, size: 14, color: Colors.grey),
                        const SizedBox(width: 4),
                        Text(
                          event.location,
                          style: const TextStyle(
                            fontSize: 13,
                            color: Colors.grey,
                          ),
                        ),
                      ],
                    ),
                  ],
                  const SizedBox(height: 4),
                  _HostsLine(event: event),
                ],
              ),
            ),
            const SizedBox(width: 8),
            IconButton(
              tooltip: 'Edit',
              icon: const Icon(Icons.edit_outlined),
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
    );
  }
}
