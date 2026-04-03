import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/utils/file_download.dart';
import 'package:pda/utils/ics_generator.dart';
import 'package:pda/utils/launcher.dart';
import 'package:pda/utils/app_icons.dart';
import 'package:pda/models/event.dart';

class EventDetailHostChip extends StatelessWidget {
  final ({String id, String name, String photoUrl}) host;

  const EventDetailHostChip({super.key, required this.host});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final hasPhoto = host.photoUrl.isNotEmpty;
    final initials = host.name.isNotEmpty ? host.name[0].toUpperCase() : '?';

    return InkWell(
      onTap: host.id.isNotEmpty
          ? () => context.push('/members/${host.id}')
          : null,
      borderRadius: BorderRadius.circular(20),
      child: Container(
        padding: const EdgeInsets.fromLTRB(4, 4, 12, 4),
        decoration: BoxDecoration(
          color: cs.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(20),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (hasPhoto)
              CircleAvatar(
                radius: 14,
                backgroundImage: NetworkImage(host.photoUrl),
              )
            else
              CircleAvatar(
                radius: 14,
                backgroundColor: cs.primaryContainer,
                child: Text(
                  initials,
                  style: TextStyle(
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                    color: cs.onPrimaryContainer,
                  ),
                ),
              ),
            const SizedBox(width: 8),
            Text(
              host.name,
              style: TextStyle(fontSize: 15, color: cs.onSurface),
            ),
          ],
        ),
      ),
    );
  }
}

class EventDetailRow extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color? color;

  const EventDetailRow({
    super.key,
    required this.icon,
    required this.text,
    this.color,
  });

  @override
  Widget build(BuildContext context) {
    final effectiveColor =
        color ?? Theme.of(context).colorScheme.onSurfaceVariant;
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(icon, size: 18, color: effectiveColor),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(fontSize: 15, color: effectiveColor),
          ),
        ),
      ],
    );
  }
}

class EventActionChip extends StatelessWidget {
  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;

  const EventActionChip({
    super.key,
    required this.tooltip,
    required this.icon,
    required this.onPressed,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Tooltip(
      message: tooltip,
      child: Material(
        color: cs.surfaceContainerHighest.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(12),
        child: InkWell(
          onTap: onPressed,
          borderRadius: BorderRadius.circular(12),
          child: Padding(
            padding: const EdgeInsets.all(9),
            child: Icon(icon, size: 17, color: cs.onSurfaceVariant),
          ),
        ),
      ),
    );
  }
}

enum CalendarOption { google, apple, download }

class CalendarMenuChip extends StatelessWidget {
  final Event event;

  const CalendarMenuChip({super.key, required this.event});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Tooltip(
      message: 'add to calendar',
      child: Material(
        color: cs.surfaceContainerHighest.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(12),
        child: PopupMenuButton<CalendarOption>(
          tooltip: 'add to calendar',
          onSelected: (option) {
            switch (option) {
              case CalendarOption.google:
                openUrl(googleCalendarUrl(event));
              case CalendarOption.apple:
                final ics = generateEventIcs(event);
                downloadFile(ics, '${event.title}.ics', 'text/calendar');
              case CalendarOption.download:
                final ics = generateEventIcs(event);
                downloadFile(ics, '${event.title}.ics', 'text/calendar');
            }
          },
          itemBuilder: (_) => const [
            PopupMenuItem(
              value: CalendarOption.google,
              child: Text('google calendar'),
            ),
            PopupMenuItem(
              value: CalendarOption.apple,
              child: Text('apple calendar'),
            ),
            PopupMenuItem(
              value: CalendarOption.download,
              child: Text('download .ics'),
            ),
          ],
          padding: EdgeInsets.zero,
          child: Padding(
            padding: const EdgeInsets.all(9),
            child: Icon(
              AppIcons.calendar,
              size: 17,
              color: cs.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }
}

class EventLinkRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String url;

  const EventLinkRow({
    super.key,
    required this.icon,
    required this.label,
    required this.url,
  });

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return InkWell(
      onTap: () => openUrl(url),
      borderRadius: BorderRadius.circular(4),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(icon, size: 18, color: color),
          const SizedBox(width: 10),
          Expanded(
            child: Text(
              label,
              style: TextStyle(
                fontSize: 15,
                color: color,
                decoration: TextDecoration.none,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
