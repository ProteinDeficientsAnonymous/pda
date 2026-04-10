import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/utils/app_icons.dart';
import 'package:pda/utils/share.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/widgets/embedded_event_poll.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/screens/calendar/event_detail_widgets.dart';
import 'package:pda/screens/calendar/event_member_section.dart';
export 'event_form_dialog.dart'
    show EventFormDialog, EventFormResult, showEventForm;

/// Shows the event detail panel as a side panel (wide) or navigates to the
/// full event page (narrow).
void showEventDetail(BuildContext context, Event event) {
  if (event.photoUrl.isNotEmpty) {
    precacheImage(NetworkImage(event.photoUrl), context);
  }
  final width = MediaQuery.sizeOf(context).width;
  if (width >= 720) {
    _showSidePanel(context, event);
  } else {
    context.push('/events/${event.id}');
  }
}

void _showSidePanel(BuildContext context, Event event) {
  showDialog(
    context: context,
    builder: (ctx) => Align(
      alignment: Alignment.centerRight,
      child: Material(
        child: SizedBox(
          width: 420,
          height: double.infinity,
          child: EventDetailContent(
            event: event,
            onCancelled: () => Navigator.of(ctx).pop(),
          ),
        ),
      ),
    ),
  );
}

List<Widget> _buildDateTimeRows(
  String Function(DateTime) dateFmt,
  DateTime start,
  DateTime? end,
) {
  const style = TextStyle(fontSize: 15, height: 1.4);
  if (end == null) {
    return [
      Text(dateFmt(start), style: style),
      const SizedBox(height: 4),
      Text(formatTime(start), style: style),
    ];
  }
  final sameDay =
      start.year == end.year &&
      start.month == end.month &&
      start.day == end.day;
  if (sameDay) {
    return [
      Text(dateFmt(start), style: style),
      const SizedBox(height: 4),
      Text('${formatTime(start)} \u2013 ${formatTime(end)}', style: style),
    ];
  }
  return [
    Text(
      '${dateFmt(start)}, ${formatTime(start)} \u2013 '
      '${dateFmt(end)}, ${formatTime(end)}',
      style: style,
    ),
  ];
}

class EventDetailContent extends ConsumerWidget {
  final Event event;
  final ScrollController? scrollController;
  final bool fullPage;
  final VoidCallback? onCancelled;

  const EventDetailContent({
    super.key,
    required this.event,
    this.scrollController,
    this.fullPage = false,
    this.onCancelled,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Fetch the full event detail (with links, RSVP, guests) from the detail
    // endpoint. Falls back to the list-level event while loading.
    final detailAsync = ref.watch(eventDetailProvider(event.id));
    final liveEvent = detailAsync.value ?? event;

    final start = liveEvent.startDatetime.toLocal();
    final end = liveEvent.endDatetime?.toLocal();
    String formatDate(DateTime d) =>
        DateFormat('EEEE, MMMM d, y').format(d).toLowerCase();

    return SelectionArea(
      child: ListView(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
        children: [
          _EventPhoto(event: liveEvent),
          Row(
            crossAxisAlignment: CrossAxisAlignment.center,
            children: [
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 16,
                          vertical: 10,
                        ),
                        decoration: BoxDecoration(
                          color: Theme.of(
                            context,
                          ).colorScheme.primaryContainer.withValues(alpha: 0.5),
                          borderRadius: BorderRadius.circular(20),
                        ),
                        child: Text(
                          liveEvent.title,
                          style: Theme.of(context).textTheme.headlineSmall,
                        ),
                      ),
                      if (liveEvent.status == EventStatus.cancelled ||
                          liveEvent.eventType == EventType.official ||
                          liveEvent.visibility == PageVisibility.membersOnly ||
                          liveEvent.visibility ==
                              PageVisibility.inviteOnly) ...[
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 6,
                          children: [
                            if (liveEvent.status == EventStatus.cancelled)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 4,
                                ),
                                decoration: BoxDecoration(
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.errorContainer,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  'cancelled',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.onErrorContainer,
                                  ),
                                ),
                              ),
                            if (liveEvent.eventType == EventType.official)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 4,
                                ),
                                decoration: BoxDecoration(
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.secondaryContainer,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  'official pda event',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.onSecondaryContainer,
                                  ),
                                ),
                              ),
                            if (liveEvent.visibility ==
                                PageVisibility.membersOnly)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 4,
                                ),
                                decoration: BoxDecoration(
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.tertiaryContainer,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  'pda members only',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.onTertiaryContainer,
                                  ),
                                ),
                              ),
                            if (liveEvent.visibility ==
                                PageVisibility.inviteOnly)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 4,
                                ),
                                decoration: BoxDecoration(
                                  color: Theme.of(
                                    context,
                                  ).colorScheme.errorContainer,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  'invite only',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color: Theme.of(
                                      context,
                                    ).colorScheme.onErrorContainer,
                                  ),
                                ),
                              ),
                          ],
                        ),
                      ],
                    ],
                  ),
                ),
              ),
              const SizedBox(width: 8),
              CalendarMenuChip(event: liveEvent),
              const SizedBox(width: 4),
              EventActionChip(
                tooltip: 'share event',
                icon: AppIcons.share,
                onPressed: () {
                  final link = Uri.base
                      .replace(path: '/events/${liveEvent.id}', query: null)
                      .toString();
                  shareUrl(link);
                },
              ),
              if (!fullPage) ...[
                const SizedBox(width: 4),
                EventActionChip(
                  tooltip: 'open full page',
                  icon: AppIcons.openExternal,
                  onPressed: () {
                    Navigator.of(context).pop();
                    context.push('/events/${liveEvent.id}');
                  },
                ),
              ],
            ],
          ),
          const SizedBox(height: 16),
          EventSectionCard(
            label: EventDetailLabel.when,
            child: liveEvent.hasPoll
                ? EmbeddedEventPoll(event: liveEvent)
                : Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: liveEvent.datetimeTbd
                        ? [
                            const Text(
                              'date & time tbd',
                              style: TextStyle(fontSize: 15, height: 1.4),
                            ),
                          ]
                        : _buildDateTimeRows(formatDate, start, end),
                  ),
          ),
          if (liveEvent.description.isNotEmpty) ...[
            const SizedBox(height: 12),
            EventSectionCard(
              label: EventDetailLabel.about,
              child: Text(
                liveEvent.description,
                style: const TextStyle(fontSize: 15, height: 1.6),
              ),
            ),
          ],
          const SizedBox(height: 12),
          EventMemberSection(
            event: liveEvent,
            location: liveEvent.location,
            onCancelled: onCancelled,
          ),
        ],
      ),
    );
  }
}

class _EventPhoto extends StatelessWidget {
  final Event event;

  const _EventPhoto({required this.event});

  @override
  Widget build(BuildContext context) {
    if (event.photoUrl.isEmpty) return const SizedBox.shrink();

    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: ClipRRect(
        borderRadius: BorderRadius.circular(12),
        child: Image.network(
          event.photoUrl,
          fit: BoxFit.contain,
          frameBuilder: (context, child, frame, wasSynchronouslyLoaded) {
            if (wasSynchronouslyLoaded) return child;
            return AnimatedOpacity(
              opacity: frame == null ? 0.0 : 1.0,
              duration: const Duration(milliseconds: 300),
              curve: Curves.easeOut,
              child: child,
            );
          },
          loadingBuilder: (context, child, loadingProgress) {
            if (loadingProgress == null) return child;
            return AspectRatio(
              aspectRatio: 16 / 9,
              child: ColoredBox(
                color: Theme.of(context).colorScheme.surfaceContainerHighest,
              ),
            );
          },
        ),
      ),
    );
  }
}
