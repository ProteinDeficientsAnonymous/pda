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

  Future<void> _confirmCancel(BuildContext context, WidgetRef ref) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('cancel event'),
        content: Text(
          'cancel "${event.title}"? attendees will see it\'s been cancelled.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('nevermind'),
          ),
          FilledButton(
            style: FilledButton.styleFrom(
              backgroundColor: Theme.of(ctx).colorScheme.error,
            ),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('cancel event'),
          ),
        ],
      ),
    );

    if (confirmed != true) return;

    try {
      final api = ref.read(apiClientProvider);
      await api.delete('/api/community/events/${event.id}/');
      ref.invalidate(eventsProvider);
      ref.invalidate(cancelledEventsProvider);
      _log.info('cancelled event ${event.id}');
    } catch (e, st) {
      _log.warning('failed to cancel event', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  Future<void> _doUncancel(BuildContext context, WidgetRef ref) async {
    try {
      await uncancelEvent(ref, event.id);
      _log.info('uncancelled event ${event.id}');
      if (context.mounted) showSnackBar(context, 'event reinstated');
    } catch (e, st) {
      _log.warning('failed to uncancel event', e, st);
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dateFmt = DateFormat('EEE, MMM d');

    final (bg, fg) = eventColors(event.id, Theme.of(context).brightness);

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
                        if (event.status == EventStatus.cancelled) ...[
                          const SizedBox(width: 8),
                          Container(
                            padding: const EdgeInsets.symmetric(
                              horizontal: 6,
                              vertical: 2,
                            ),
                            decoration: BoxDecoration(
                              color: Theme.of(
                                context,
                              ).colorScheme.errorContainer,
                              borderRadius: BorderRadius.circular(4),
                            ),
                            child: Text(
                              'cancelled',
                              style: TextStyle(
                                fontSize: 10,
                                fontWeight: FontWeight.w600,
                                color: Theme.of(
                                  context,
                                ).colorScheme.onErrorContainer,
                              ),
                            ),
                          ),
                        ],
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
              if (event.status != EventStatus.cancelled)
                IconButton(
                  tooltip: 'Edit',
                  icon: Icon(Icons.edit_outlined, color: fg.withAlpha(178)),
                  onPressed: () => _showEditDialog(context, ref),
                ),
              if (event.status == EventStatus.cancelled)
                IconButton(
                  tooltip: 'Uncancel',
                  icon: const Icon(Icons.restore),
                  onPressed: () => _doUncancel(context, ref),
                )
              else
                IconButton(
                  tooltip: 'Cancel event',
                  icon: Icon(
                    Icons.cancel_outlined,
                    color: Theme.of(context).colorScheme.error,
                  ),
                  onPressed: () => _confirmCancel(context, ref),
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
