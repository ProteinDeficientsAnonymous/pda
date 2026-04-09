import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart' show DateFormat;
import 'package:logging/logging.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_colors.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/create_datetime_poll.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/time_format.dart';

final _log = Logger('EventManagement');

class EventManagementRow extends ConsumerWidget {
  final Event event;

  const EventManagementRow({super.key, required this.event});

  Future<void> _showEditDialog(BuildContext context, WidgetRef ref) async {
    final result = await showEventForm(context, event: event);
    if (result == null) return;
    try {
      final api = ref.read(apiClientProvider);
      await api.patch('/api/community/events/${event.id}/', data: result.data);
      if (result.photo != null) {
        await uploadEventPhoto(
          ref,
          event.id,
          result.photo!,
          oldPhotoUrl: event.photoUrl,
        );
      } else if (result.removePhoto) {
        await deleteEventPhoto(ref, event.id);
      }
      if (result.datetimePollOptions.isNotEmpty) {
        await createDatetimePoll(
          ref: ref,
          eventId: event.id,
          eventTitle: result.data['title'] as String,
          options: result.datetimePollOptions,
        );
      }
      ref.invalidate(eventsProvider);
      _log.info('edited event ${event.id}');
    } catch (e, st) {
      _log.warning('failed to edit event', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  Future<void> _confirmDelete(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
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
      _log.info('deleted event ${event.id}');
    } catch (e, st) {
      _log.warning('failed to delete event', e, st);
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
