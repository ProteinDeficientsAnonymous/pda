import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:image_picker/image_picker.dart';
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

export 'event_form_dialog.dart' show EventFormDialog;

/// Shows the event detail panel as a bottom sheet (narrow) or side panel (wide).
void showEventDetail(BuildContext context, Event event) {
  final width = MediaQuery.sizeOf(context).width;
  if (width >= 720) {
    _showSidePanel(context, event);
  } else {
    _showBottomSheet(context, event);
  }
}

void _showBottomSheet(BuildContext context, Event event) {
  showModalBottomSheet(
    context: context,
    isScrollControlled: true,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(16)),
    ),
    builder:
        (_) => DraggableScrollableSheet(
          initialChildSize: 0.6,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder:
              (ctx, controller) => EventDetailContent(
                event: event,
                scrollController: controller,
              ),
        ),
  );
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
  if (end == null) {
    return [
      _DetailRow(icon: Icons.today_outlined, text: dateFmt(start)),
      const SizedBox(height: 8),
      _DetailRow(icon: Icons.schedule_outlined, text: formatTime(start)),
    ];
  }
  final sameDay =
      start.year == end.year &&
      start.month == end.month &&
      start.day == end.day;
  if (sameDay) {
    return [
      _DetailRow(icon: Icons.today_outlined, text: dateFmt(start)),
      const SizedBox(height: 8),
      _DetailRow(
        icon: Icons.schedule_outlined,
        text: '${formatTime(start)} \u2013 ${formatTime(end)}',
      ),
    ];
  }
  return [
    _DetailRow(
      icon: Icons.calendar_today,
      text:
          '${dateFmt(start)}, ${formatTime(start)} \u2013 '
          '${dateFmt(end)}, ${formatTime(end)}',
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

    final hostNames = <String>[];
    if (liveEvent.createdByName != null) {
      hostNames.add(liveEvent.createdByName!);
    }
    hostNames.addAll(liveEvent.coHostNames);

    return SelectionArea(
      child: ListView(
        controller: scrollController,
        padding: const EdgeInsets.fromLTRB(24, 16, 24, 32),
        children: [
          if (liveEvent.photoUrl.isNotEmpty)
            Padding(
              padding: const EdgeInsets.only(bottom: 16),
              child: ClipRRect(
                borderRadius: BorderRadius.circular(12),
                child: Image.network(
                  liveEvent.photoUrl,
                  height: 200,
                  width: double.infinity,
                  fit: BoxFit.cover,
                ),
              ),
            ),
          Row(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.only(top: 12),
                  child: Text(
                    liveEvent.title,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ),
              ),
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
          ..._buildDateTimeRows(formatDate, start, end),
          if (hostNames.isNotEmpty) ...[
            const SizedBox(height: 8),
            _DetailRow(
              icon: Icons.person_pin_outlined,
              text: hostNames.join(', '),
            ),
          ],
          if (liveEvent.description.isNotEmpty) ...[
            const SizedBox(height: 16),
            Text(
              liveEvent.description,
              style: const TextStyle(fontSize: 15, height: 1.6),
            ),
          ],
          const SizedBox(height: 24),
          const Divider(),
          const SizedBox(height: 8),
          _MemberSection(event: liveEvent, location: liveEvent.location),
        ],
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final IconData icon;
  final String text;

  const _DetailRow({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    return Row(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Icon(
          icon,
          size: 18,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        const SizedBox(width: 10),
        Expanded(
          child: Text(
            text,
            style: TextStyle(
              fontSize: 15,
              color: Theme.of(context).colorScheme.onSurfaceVariant,
            ),
          ),
        ),
      ],
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
      onTap: () {
        Clipboard.setData(ClipboardData(text: url));
        showSnackBar(context, 'Link copied to clipboard');
      },
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
                decoration: TextDecoration.underline,
                decorationColor: color,
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

  Future<void> _pickPhoto() async {
    final image = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      maxWidth: 1200,
      maxHeight: 800,
      imageQuality: 85,
    );
    if (image == null) return;
    setState(() => _loading = true);
    try {
      await uploadEventPhoto(ref, widget.event.id, image);
      if (mounted) showSnackBar(context, 'photo updated ✓');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t upload photo — try again');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _removePhoto() async {
    setState(() => _loading = true);
    try {
      await deleteEventPhoto(ref, widget.event.id);
      if (mounted) showSnackBar(context, 'photo removed');
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t remove photo — try again');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

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
        showErrorSnackBar(context, 'Failed to delete event: $e');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _edit() async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (ctx) => EventFormDialog(event: widget.event),
    );
    if (result == null) return;

    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.patch(
        '/api/community/events/${widget.event.id}/',
        data: result,
      );
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'Failed to update event: $e');
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

    final hasPhoto = widget.event.photoUrl.isNotEmpty;

    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: [
        OutlinedButton.icon(
          onPressed: _pickPhoto,
          icon: Icon(
            hasPhoto
                ? Icons.photo_outlined
                : Icons.add_photo_alternate_outlined,
            size: 16,
          ),
          label: Text(hasPhoto ? 'change photo' : 'add photo'),
        ),
        if (hasPhoto)
          OutlinedButton.icon(
            onPressed: _removePhoto,
            icon: const Icon(Icons.hide_image_outlined, size: 16),
            label: const Text('remove photo'),
          ),
        OutlinedButton.icon(
          onPressed: _edit,
          icon: const Icon(Icons.edit_outlined, size: 16),
          label: const Text('edit'),
        ),
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
      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (location.isNotEmpty) ...[
            _DetailRow(icon: Icons.location_on_outlined, text: location),
            const SizedBox(height: 8),
          ],
          if (event.whatsappLink.isNotEmpty) ...[
            _LinkRow(
              icon: Icons.chat_bubble_outline,
              label: 'WhatsApp group',
              url: event.whatsappLink,
            ),
            const SizedBox(height: 8),
          ],
          if (event.partifulLink.isNotEmpty) ...[
            _LinkRow(
              icon: Icons.celebration,
              label: 'Partiful',
              url: event.partifulLink,
            ),
            const SizedBox(height: 8),
          ],
          if (event.otherLink.isNotEmpty) ...[
            _LinkRow(
              icon: Icons.link_outlined,
              label: event.otherLink,
              url: event.otherLink,
            ),
            const SizedBox(height: 8),
          ],
          if (event.surveySlugs.isNotEmpty) ...[
            const SizedBox(height: 8),
            ...event.surveySlugs.map(
              (slug) => Padding(
                padding: const EdgeInsets.only(bottom: 4),
                child: InkWell(
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
            ),
          ],
          if (event.rsvpEnabled) ...[
            const SizedBox(height: 8),
            RSVPSection(event: event),
            const SizedBox(height: 16),
            const Divider(),
            const SizedBox(height: 8),
          ],
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

  // null = phone step, true = login step, false = join step
  bool? _isMember;
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
      final exists = (res.data as Map<String, dynamic>)['exists'] as bool;
      setState(() => _isMember = exists);
    } catch (e) {
      setState(() => _error = 'Something went wrong. Please try again.');
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
      setState(() => _error = 'Incorrect password. Please try again.');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Phone step
    if (_isMember == null) {
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
    if (_isMember == true) {
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
                    onPressed: () => setState(() => _isMember = null),
                    child: const Text('back'),
                  ),
                ],
              ),
            ],
          ),
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
            onPressed: () => setState(() => _isMember = null),
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
