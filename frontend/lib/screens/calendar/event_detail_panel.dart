import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/utils/file_download.dart';
import 'package:pda/utils/ics_generator.dart';
import 'package:pda/utils/launcher.dart';
import 'package:pda/utils/app_icons.dart';
import 'package:pda/utils/share.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/loading_button.dart';
import 'package:pda/widgets/phone_form_field.dart';
import 'event_form_dialog.dart';
import 'rsvp_section.dart';
import 'package:pda/config/constants.dart';

export 'event_form_dialog.dart' show EventFormDialog, EventFormResult;

/// Shows the event detail panel as a side panel (wide) or navigates to the
/// full event page (narrow).
void showEventDetail(BuildContext context, Event event) {
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
    builder:
        (ctx) => Align(
          alignment: Alignment.centerRight,
          child: Material(
            child: SizedBox(
              width: 420,
              height: double.infinity,
              child: EventDetailContent(event: event),
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
  final style = const TextStyle(fontSize: 15, height: 1.4);
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

  const EventDetailContent({
    super.key,
    required this.event,
    this.scrollController,
    this.fullPage = false,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    // Fetch the full event detail (with links, RSVP, guests) from the detail
    // endpoint. Falls back to the list-level event while loading.
    final detailAsync = ref.watch(eventDetailProvider(event.id));
    final liveEvent = detailAsync.valueOrNull ?? event;

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
                      if (liveEvent.eventType == EventType.official ||
                          liveEvent.visibility ==
                              PageVisibility.membersOnly) ...[
                        const SizedBox(height: 6),
                        Wrap(
                          spacing: 6,
                          children: [
                            if (liveEvent.eventType == EventType.official)
                              Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 10,
                                  vertical: 4,
                                ),
                                decoration: BoxDecoration(
                                  color:
                                      Theme.of(
                                        context,
                                      ).colorScheme.secondaryContainer,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  'official pda event',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color:
                                        Theme.of(
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
                                  color:
                                      Theme.of(
                                        context,
                                      ).colorScheme.tertiaryContainer,
                                  borderRadius: BorderRadius.circular(12),
                                ),
                                child: Text(
                                  'members only',
                                  style: TextStyle(
                                    fontSize: 11,
                                    fontWeight: FontWeight.w600,
                                    color:
                                        Theme.of(
                                          context,
                                        ).colorScheme.onTertiaryContainer,
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
              _CalendarMenuChip(event: liveEvent),
              const SizedBox(width: 4),
              _ActionChip(
                tooltip: 'share event',
                icon: AppIcons.share,
                onPressed: () {
                  final link =
                      Uri.base
                          .replace(path: '/events/${liveEvent.id}', query: '')
                          .toString();
                  shareUrl(link, subject: liveEvent.title);
                },
              ),
              if (!fullPage) ...[
                const SizedBox(width: 4),
                _ActionChip(
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
          _SectionCard(
            label: EventDetailLabel.when,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children:
                  liveEvent.datetimeTbd
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
            _SectionCard(
              label: EventDetailLabel.about,
              child: Text(
                liveEvent.description,
                style: const TextStyle(fontSize: 15, height: 1.6),
              ),
            ),
          ],
          const SizedBox(height: 12),
          _MemberSection(event: liveEvent, location: liveEvent.location),
        ],
      ),
    );
  }
}

class _SectionCard extends StatelessWidget {
  final String label;
  final Widget child;

  const _SectionCard({required this.label, required this.child});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHighest.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: cs.onSurfaceVariant,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }
}

class _HostChip extends StatelessWidget {
  final ({String id, String name, String photoUrl}) host;

  const _HostChip({required this.host});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final hasPhoto = host.photoUrl.isNotEmpty;
    final initials = host.name.isNotEmpty ? host.name[0].toUpperCase() : '?';

    return InkWell(
      onTap:
          host.id.isNotEmpty ? () => context.push('/members/${host.id}') : null,
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

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String text;
  final Color? color;

  const _DetailRow({required this.icon, required this.text, this.color});

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
          height: 200,
          width: double.infinity,
          fit: BoxFit.cover,
        ),
      ),
    );
  }
}

class _ActionChip extends StatelessWidget {
  final String tooltip;
  final IconData icon;
  final VoidCallback onPressed;

  const _ActionChip({
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

enum _CalendarOption { google, apple, download }

class _CalendarMenuChip extends StatelessWidget {
  final Event event;

  const _CalendarMenuChip({required this.event});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Tooltip(
      message: 'add to calendar',
      child: Material(
        color: cs.surfaceContainerHighest.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(12),
        child: PopupMenuButton<_CalendarOption>(
          tooltip: 'add to calendar',
          onSelected: (option) {
            switch (option) {
              case _CalendarOption.google:
                openUrl(googleCalendarUrl(event));
              case _CalendarOption.apple:
                final ics = generateEventIcs(event);
                downloadFile(ics, '${event.title}.ics', 'text/calendar');
              case _CalendarOption.download:
                final ics = generateEventIcs(event);
                downloadFile(ics, '${event.title}.ics', 'text/calendar');
            }
          },
          itemBuilder:
              (_) => const [
                PopupMenuItem(
                  value: _CalendarOption.google,
                  child: Text('google calendar'),
                ),
                PopupMenuItem(
                  value: _CalendarOption.apple,
                  child: Text('apple calendar'),
                ),
                PopupMenuItem(
                  value: _CalendarOption.download,
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

class _LinkRow extends StatelessWidget {
  final IconData icon;
  final String label;
  final String url;

  const _LinkRow({required this.icon, required this.label, required this.url});

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

class _AdminActions extends ConsumerStatefulWidget {
  final Event event;

  const _AdminActions({required this.event});

  @override
  ConsumerState<_AdminActions> createState() => _AdminActionsState();
}

class _AdminActionsState extends ConsumerState<_AdminActions> {
  bool _loading = false;

  Future<void> _delete() async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Delete event'),
            content: Text(
              'Delete "${widget.event.title}"? This cannot be undone.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.pop(ctx, false),
                child: const Text('Cancel'),
              ),
              FilledButton(
                onPressed: () => Navigator.pop(ctx, true),
                child: const Text('Delete'),
              ),
            ],
          ),
    );
    if (confirmed != true) return;

    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.delete('/api/community/events/${widget.event.id}/');
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
      if (mounted) Navigator.of(context).pop();
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _edit() async {
    final result = await showDialog<EventFormResult>(
      context: context,
      builder: (ctx) => EventFormDialog(event: widget.event),
    );
    if (result == null) return;

    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.patch(
        '/api/community/events/${widget.event.id}/',
        data: result.data,
      );
      if (result.photo != null) {
        await uploadEventPhoto(ref, widget.event.id, result.photo!);
      } else if (result.removePhoto) {
        await deleteEventPhoto(ref, widget.event.id);
      }
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    final user = ref.watch(authProvider).valueOrNull;
    if (user == null) return const SizedBox.shrink();

    final isCreator = widget.event.createdById == user.id;
    final isManager = user.hasPermission(Permission.manageEvents);
    if (!isCreator && !isManager) return const SizedBox.shrink();

    return Row(
      mainAxisAlignment: MainAxisAlignment.center,
      children: [
        OutlinedButton.icon(
          onPressed: _edit,
          icon: const Icon(Icons.edit_outlined, size: 16),
          label: const Text('edit'),
        ),
        const SizedBox(width: 12),
        OutlinedButton.icon(
          onPressed: _delete,
          icon: Icon(
            Icons.delete_outline,
            size: 16,
            color: Theme.of(context).colorScheme.error,
          ),
          label: Text(
            'delete',
            style: TextStyle(color: Theme.of(context).colorScheme.error),
          ),
          style: OutlinedButton.styleFrom(
            side: BorderSide(color: Theme.of(context).colorScheme.error),
          ),
        ),
      ],
    );
  }
}

/// Shows member-only content (location, links, RSVP, admin actions) or a
/// login/join prompt for unauthenticated visitors.
class _MemberSection extends ConsumerWidget {
  final Event event;
  final String location;
  const _MemberSection({required this.event, required this.location});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    if (user != null) {
      // Build host list: creator first (no photo), then co-hosts (with photos)
      final hosts = <({String id, String name, String photoUrl})>[];
      if (event.createdByName != null) {
        hosts.add((
          id: event.createdById ?? '',
          name: event.createdByName!,
          photoUrl: '',
        ));
      }
      for (var i = 0; i < event.coHostNames.length; i++) {
        hosts.add((
          id: i < event.coHostIds.length ? event.coHostIds[i] : '',
          name: event.coHostNames[i],
          photoUrl:
              i < event.coHostPhotoUrls.length ? event.coHostPhotoUrls[i] : '',
        ));
      }

      final detailRows = <Widget>[
        if (location.isNotEmpty)
          Semantics(
            button: true,
            label: 'Open $location in maps',
            child: InkWell(
              onTap: () => openLocationInMaps(location),
              borderRadius: BorderRadius.circular(4),
              child: _DetailRow(
                icon: Icons.location_on_outlined,
                text: location.split(', ').first,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
        if (event.whatsappLink.isNotEmpty)
          _LinkRow(
            icon: Icons.chat_bubble_outline,
            label: 'WhatsApp group',
            url: event.whatsappLink,
          ),
        if (event.partifulLink.isNotEmpty)
          _LinkRow(
            icon: Icons.celebration,
            label: 'Partiful',
            url: event.partifulLink,
          ),
        if (event.otherLink.isNotEmpty)
          _LinkRow(
            icon: Icons.link_outlined,
            label: event.otherLink,
            url: event.otherLink,
          ),
        if (event.price.isNotEmpty)
          _DetailRow(icon: Icons.attach_money, text: event.price),
        if (event.venmoLink.isNotEmpty)
          _LinkRow(icon: Icons.payment, label: 'venmo', url: event.venmoLink),
        if (event.cashappLink.isNotEmpty)
          _LinkRow(
            icon: Icons.monetization_on_outlined,
            label: 'cash app',
            url: event.cashappLink,
          ),
        if (event.zelleInfo.isNotEmpty)
          _DetailRow(
            icon: Icons.account_balance_outlined,
            text: 'zelle: ${event.zelleInfo}',
          ),
        ...event.surveySlugs.map(
          (slug) => InkWell(
            onTap: () => context.go('/surveys/$slug'),
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                children: [
                  Icon(
                    Icons.rate_review_rounded,
                    size: 18,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 8),
                  Text(
                    'give feedback',
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.primary,
                      fontWeight: FontWeight.w500,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ];

      final invitedChips = [
        for (var i = 0; i < event.invitedUserNames.length; i++)
          _HostChip(
            host: (
              id:
                  i < event.invitedUserIds.length
                      ? event.invitedUserIds[i]
                      : '',
              name: event.invitedUserNames[i],
              photoUrl:
                  i < event.invitedUserPhotoUrls.length
                      ? event.invitedUserPhotoUrls[i]
                      : '',
            ),
          ),
      ];

      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (hosts.isNotEmpty)
            _SectionCard(
              label:
                  hosts.length > 1
                      ? EventDetailLabel.coHosts
                      : EventDetailLabel.host,
              child: Wrap(
                spacing: 12,
                runSpacing: 8,
                children: [for (final host in hosts) _HostChip(host: host)],
              ),
            ),
          if (invitedChips.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SectionCard(
              label: EventDetailLabel.invited,
              child: Wrap(spacing: 12, runSpacing: 8, children: invitedChips),
            ),
          ],
          if (detailRows.isNotEmpty) ...[
            const SizedBox(height: 12),
            _SectionCard(
              label: EventDetailLabel.details,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var i = 0; i < detailRows.length; i++) ...[
                    detailRows[i],
                    if (i < detailRows.length - 1) const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
          ],
          if (event.rsvpEnabled) ...[
            const SizedBox(height: 12),
            _SectionCard(
              label: EventDetailLabel.rsvp,
              child: RSVPSection(event: event),
            ),
          ],
          const SizedBox(height: 12),
          _AdminActions(event: event),
        ],
      );
    }
    return _LoginOrJoinSection(event: event);
  }
}

/// Shown to unauthenticated visitors. Collects phone number, checks if they're
/// a member, then either prompts login or prompts them to submit a join request.
class _LoginOrJoinSection extends ConsumerStatefulWidget {
  final Event event;
  const _LoginOrJoinSection({required this.event});

  @override
  ConsumerState<_LoginOrJoinSection> createState() =>
      _LoginOrJoinSectionState();
}

class _LoginOrJoinSectionState extends ConsumerState<_LoginOrJoinSection> {
  String _phoneNumber = '';
  final _passwordCtrl = TextEditingController();
  final _phoneKey = GlobalKey<FormState>();
  final _loginKey = GlobalKey<FormState>();

  // null = phone step, "member" / "pending" / "unknown"
  String? _phoneStatus;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _checkPhone() async {
    if (!(_phoneKey.currentState?.validate() ?? false)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final res = await api.post(
        '/api/community/check-phone/',
        data: {'phone_number': _phoneNumber},
      );
      final status = (res.data as Map<String, dynamic>)['status'] as String;
      setState(() => _phoneStatus = status);
    } catch (e) {
      setState(() => _error = 'something went wrong — try again');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _login() async {
    if (!(_loginKey.currentState?.validate() ?? false)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .login(_phoneNumber, _passwordCtrl.text);
    } catch (e) {
      setState(() => _error = 'incorrect password — try again');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Phone step
    if (_phoneStatus == null) {
      return _JuicyGate(
        headline: '🔒 log in to see the juicy details',
        subtext:
            'links, RSVPs & more are for members only — enter your number to get in',
        error: _error,
        child: Form(
          key: _phoneKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              PhoneFormField(onChanged: (number) => _phoneNumber = number),
              const SizedBox(height: 8),
              LoadingButton(
                label: 'continue',
                onPressed: _checkPhone,
                loading: _loading,
              ),
            ],
          ),
        ),
      );
    }

    // Login step (member found)
    if (_phoneStatus == 'member') {
      return _JuicyGate(
        headline: '👋 hey, welcome back!',
        subtext: 'pop in your password and we\'ll get you in',
        error: _error,
        child: Form(
          key: _loginKey,
          child: Column(
            children: [
              TextFormField(
                controller: _passwordCtrl,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  border: OutlineInputBorder(),
                  isDense: true,
                ),
                obscureText: true,
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Required';
                  return null;
                },
                onFieldSubmitted: (_) => _login(),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  LoadingButton(
                    label: 'log in',
                    onPressed: _login,
                    loading: _loading,
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () => setState(() => _phoneStatus = null),
                    child: const Text('back'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }

    // Request in review
    if (_phoneStatus == 'pending') {
      return _JuicyGate(
        headline: '⏳ your request is in review',
        subtext: 'hang tight — we\'ll get back to you soon',
        error: null,
        child: TextButton(
          onPressed: () => setState(() => _phoneStatus = null),
          child: const Text('back'),
        ),
      );
    }

    // Not a member — prompt to join
    return _JuicyGate(
      headline: '🌱 not a member yet?',
      subtext: 'request to join the collective and unlock all the good stuff',
      error: null,
      child: Row(
        children: [
          FilledButton(
            onPressed: () => context.push('/join'),
            child: const Text('request to join'),
          ),
          const SizedBox(width: 8),
          TextButton(
            onPressed: () => setState(() => _phoneStatus = null),
            child: const Text('back'),
          ),
        ],
      ),
    );
  }
}

class _JuicyGate extends StatelessWidget {
  const _JuicyGate({
    required this.headline,
    required this.subtext,
    required this.child,
    required this.error,
  });

  final String headline;
  final String subtext;
  final Widget child;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.2),
        ),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            headline,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtext,
            style: TextStyle(
              fontSize: 13,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 12),
          child,
          if (error != null) ...[
            const SizedBox(height: 8),
            Text(
              error!,
              style: TextStyle(fontSize: 13, color: theme.colorScheme.error),
            ),
          ],
        ],
      ),
    );
  }
}
