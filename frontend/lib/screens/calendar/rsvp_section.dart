import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/config/constants.dart';

class RSVPSection extends ConsumerStatefulWidget {
  final Event event;
  const RSVPSection({super.key, required this.event});

  @override
  ConsumerState<RSVPSection> createState() => _RSVPSectionState();
}

class _RSVPSectionState extends ConsumerState<RSVPSection> {
  bool _loading = false;

  Future<void> _setRsvp(String status) async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.post(
        '/api/community/events/${widget.event.id}/rsvp/',
        data: {'status': status},
      );
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t update your rsvp — try again');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _removeRsvp() async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.delete('/api/community/events/${widget.event.id}/rsvp/');
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
    } catch (_) {
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final liveEvent =
        ref.watch(eventDetailProvider(widget.event.id)).valueOrNull ??
        widget.event;
    final myRsvp = liveEvent.myRsvp;
    final guests = liveEvent.guests;

    final attending =
        guests.where((g) => g.status == RsvpStatus.attending).toList();
    final maybe = guests.where((g) => g.status == RsvpStatus.maybe).toList();
    final cantGo = guests.where((g) => g.status == RsvpStatus.cantGo).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('rsvp', style: theme.textTheme.titleSmall),
        const SizedBox(height: 10),
        if (_loading)
          const SizedBox(
            height: 36,
            child: Center(child: CircularProgressIndicator(strokeWidth: 2)),
          )
        else
          Center(
            child: Wrap(
              spacing: 8,
              runSpacing: 8,
              alignment: WrapAlignment.center,
              children: [
                RsvpButton(
                  label: "i'm going",
                  icon: Icons.sentiment_very_satisfied_outlined,
                  activeColor: theme.colorScheme.primary,
                  isActive: myRsvp == RsvpStatus.attending,
                  onTap:
                      () =>
                          myRsvp == RsvpStatus.attending
                              ? _removeRsvp()
                              : _setRsvp(RsvpStatus.attending),
                ),
                RsvpButton(
                  label: 'maybe',
                  icon: Icons.sentiment_neutral_outlined,
                  activeColor: theme.colorScheme.tertiary,
                  isActive: myRsvp == RsvpStatus.maybe,
                  onTap:
                      () =>
                          myRsvp == RsvpStatus.maybe
                              ? _removeRsvp()
                              : _setRsvp(RsvpStatus.maybe),
                ),
                RsvpButton(
                  label: "can't make it",
                  icon: Icons.sentiment_dissatisfied_outlined,
                  activeColor: theme.colorScheme.error,
                  isActive: myRsvp == RsvpStatus.cantGo,
                  onTap:
                      () =>
                          myRsvp == RsvpStatus.cantGo
                              ? _removeRsvp()
                              : _setRsvp(RsvpStatus.cantGo),
                ),
              ],
            ),
          ),
        if (guests.isNotEmpty) ...[
          const SizedBox(height: 16),
          _GuestGroup(
            label: 'going (${attending.length})',
            guests: attending,
            color: theme.colorScheme.primary,
          ),
          _GuestGroup(
            label: 'maybe (${maybe.length})',
            guests: maybe,
            color: theme.colorScheme.tertiary,
          ),
          _GuestGroup(
            label: "can't make it (${cantGo.length})",
            guests: cantGo,
            color: theme.colorScheme.error,
          ),
        ],
      ],
    );
  }
}

class RsvpButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color activeColor;
  final bool isActive;
  final VoidCallback onTap;

  const RsvpButton({
    super.key,
    required this.label,
    required this.icon,
    required this.activeColor,
    required this.isActive,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 7),
        decoration: BoxDecoration(
          color:
              isActive
                  ? activeColor.withValues(alpha: 0.15)
                  : Theme.of(context).colorScheme.surfaceContainerHighest,
          borderRadius: BorderRadius.circular(8),
          border: Border.all(
            color: isActive ? activeColor : Colors.transparent,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              icon,
              size: 15,
              color:
                  isActive
                      ? activeColor
                      : Theme.of(context).colorScheme.onSurfaceVariant,
            ),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w500,
                color:
                    isActive
                        ? activeColor
                        : Theme.of(context).colorScheme.onSurfaceVariant,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _GuestGroup extends StatelessWidget {
  final String label;
  final List<EventGuest> guests;
  final Color color;

  const _GuestGroup({
    required this.label,
    required this.guests,
    required this.color,
  });

  @override
  Widget build(BuildContext context) {
    if (guests.isEmpty) return const SizedBox.shrink();
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w600,
              color: color,
            ),
          ),
          const SizedBox(height: 4),
          Wrap(
            spacing: 6,
            runSpacing: 4,
            children: guests.map((g) => _GuestChip(guest: g)).toList(),
          ),
        ],
      ),
    );
  }
}

class _GuestAvatar extends StatelessWidget {
  final EventGuest guest;
  const _GuestAvatar({required this.guest});

  static const double radius = 10;

  @override
  Widget build(BuildContext context) {
    if (guest.photoUrl.isNotEmpty) {
      return CircleAvatar(
        radius: radius,
        backgroundImage: NetworkImage(guest.photoUrl),
      );
    }
    final initials = guest.name.isNotEmpty ? guest.name[0].toUpperCase() : '?';
    return CircleAvatar(
      radius: radius,
      backgroundColor: Theme.of(context).colorScheme.primaryContainer,
      child: Text(
        initials,
        style: TextStyle(
          fontSize: radius * 0.9,
          fontWeight: FontWeight.w600,
          color: Theme.of(context).colorScheme.onPrimaryContainer,
        ),
      ),
    );
  }
}

class _GuestChip extends StatefulWidget {
  final EventGuest guest;

  const _GuestChip({required this.guest});

  @override
  State<_GuestChip> createState() => _GuestChipState();
}

class _GuestChipState extends State<_GuestChip> {
  bool _expanded = false;
  OverlayEntry? _overlay;
  final _link = LayerLink();

  @override
  void dispose() {
    _removeOverlay();
    super.dispose();
  }

  void _removeOverlay() {
    _overlay?.remove();
    _overlay = null;
  }

  void _showOverlay(String phone) {
    if (_overlay != null) return;
    _overlay = OverlayEntry(
      builder:
          (_) => GestureDetector(
            behavior: HitTestBehavior.translucent,
            onTap: _removeOverlay,
            child: Stack(
              children: [
                CompositedTransformFollower(
                  link: _link,
                  offset: const Offset(0, 20),
                  child: Material(
                    elevation: 4,
                    borderRadius: BorderRadius.circular(8),
                    color: Colors.grey.shade900,
                    child: Padding(
                      padding: const EdgeInsets.symmetric(
                        horizontal: 10,
                        vertical: 7,
                      ),
                      child: Row(
                        mainAxisSize: MainAxisSize.min,
                        children: [
                          Icon(
                            Icons.smartphone_outlined,
                            size: 13,
                            color: Colors.grey.shade300,
                          ),
                          const SizedBox(width: 6),
                          SelectableText(
                            phone,
                            style: TextStyle(
                              fontSize: 13,
                              fontFamily: 'monospace',
                              color: Colors.grey.shade100,
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
    );
    Overlay.of(context).insert(_overlay!);
  }

  @override
  Widget build(BuildContext context) {
    final phone = widget.guest.phone;
    final isWide = MediaQuery.sizeOf(context).width >= 720;

    if (phone == null) {
      return Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          _GuestAvatar(guest: widget.guest),
          const SizedBox(width: 6),
          Text(widget.guest.name, style: const TextStyle(fontSize: 13)),
        ],
      );
    }

    if (isWide) {
      return CompositedTransformTarget(
        link: _link,
        child: MouseRegion(
          onEnter: (_) => _showOverlay(phone),
          onExit: (_) => _removeOverlay(),
          cursor: SystemMouseCursors.basic,
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              _GuestAvatar(guest: widget.guest),
              const SizedBox(width: 6),
              Text(
                widget.guest.name,
                style: const TextStyle(
                  fontSize: 13,
                  decoration: TextDecoration.underline,
                  decorationStyle: TextDecorationStyle.dotted,
                ),
              ),
            ],
          ),
        ),
      );
    }

    // Mobile: tap to reveal
    return Semantics(
      button: true,
      label: _expanded ? 'Hide details' : 'Show details',
      excludeSemantics: true,
      child: InkWell(
        onTap: () => setState(() => _expanded = !_expanded),
        splashColor: Colors.transparent,
        highlightColor: Colors.transparent,
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                _GuestAvatar(guest: widget.guest),
                const SizedBox(width: 6),
                Text(
                  widget.guest.name,
                  style: const TextStyle(
                    fontSize: 13,
                    decoration: TextDecoration.underline,
                    decorationStyle: TextDecorationStyle.dotted,
                  ),
                ),
              ],
            ),
            if (_expanded)
              Padding(
                padding: const EdgeInsets.only(top: 2),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.smartphone_outlined,
                      size: 11,
                      color: Theme.of(context).colorScheme.onSurfaceVariant,
                    ),
                    const SizedBox(width: 3),
                    SelectableText(
                      phone,
                      style: TextStyle(
                        fontSize: 11,
                        fontFamily: 'monospace',
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ],
                ),
              ),
          ],
        ),
      ),
    );
  }
}
