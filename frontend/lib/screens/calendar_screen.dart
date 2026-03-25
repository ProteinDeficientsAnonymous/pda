import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:pda/models/event.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

class CalendarScreen extends ConsumerWidget {
  const CalendarScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(eventsProvider);

    return AppScaffold(
      title: 'Community Calendar',
      child: eventsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Failed to load events: $e')),
        data: (events) {
          if (events.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.event_note, size: 64, color: Colors.grey),
                    SizedBox(height: 16),
                    Text(
                      'No upcoming events',
                      style: TextStyle(fontSize: 18, color: Colors.grey),
                    ),
                    SizedBox(height: 8),
                    Text(
                      'Check back soon!',
                      style: TextStyle(color: Colors.grey),
                    ),
                  ],
                ),
              ),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(24),
            itemCount: events.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) => _EventCard(event: events[index]),
          );
        },
      ),
    );
  }
}

class _EventCard extends StatelessWidget {
  final Event event;

  const _EventCard({required this.event});

  @override
  Widget build(BuildContext context) {
    final dateFmt = DateFormat('EEE, MMM d · h:mm a');
    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              event.title,
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Row(
              children: [
                const Icon(Icons.schedule, size: 16, color: Colors.grey),
                const SizedBox(width: 6),
                Text(
                  '${dateFmt.format(event.startDatetime.toLocal())} — ${DateFormat('h:mm a').format(event.endDatetime.toLocal())}',
                  style: const TextStyle(color: Colors.grey),
                ),
              ],
            ),
            if (event.location.isNotEmpty) ...[
              const SizedBox(height: 4),
              Row(
                children: [
                  const Icon(Icons.place, size: 16, color: Colors.grey),
                  const SizedBox(width: 6),
                  Text(event.location, style: const TextStyle(color: Colors.grey)),
                ],
              ),
            ],
            if (event.description.isNotEmpty) ...[
              const SizedBox(height: 12),
              Text(event.description, style: const TextStyle(fontSize: 15, height: 1.5)),
            ],
          ],
        ),
      ),
    );
  }
}
