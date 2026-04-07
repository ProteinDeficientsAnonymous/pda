import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/config/constants.dart';
import 'rsvp_guest_list.dart';

final _log = Logger('RSVP');

class RSVPSection extends ConsumerStatefulWidget {
  final Event event;
  const RSVPSection({super.key, required this.event});

  @override
  ConsumerState<RSVPSection> createState() => _RSVPSectionState();
}

class _RSVPSectionState extends ConsumerState<RSVPSection> {
  bool _loading = false;
  int _plusOneCount = 0;

  Future<void> _setRsvp(String status, {int plusOneCount = 0}) async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.post(
        '/api/community/events/${widget.event.id}/rsvp/',
        data: {'status': status, 'plus_one_count': plusOneCount},
      );
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
      _log.info('rsvp set to $status for event ${widget.event.id}');
    } catch (e, st) {
      _log.warning('failed to set rsvp', e, st);
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t update your rsvp — try again');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _confirmAndSetRsvp(
    String status,
    String label, {
    int plusOneCount = 0,
  }) async {
    final user = ref.read(authProvider).value;
    final isCoHost =
        user != null &&
        (widget.event.coHostIds.contains(user.id) ||
            widget.event.createdById == user.id);

    if (isCoHost) {
      final confirmed = await showDialog<bool>(
        context: context,
        builder: (ctx) => AlertDialog(
          title: const Text('change your rsvp?'),
          content: Text(
            'you\'re a co-host of this event — are you sure you want to rsvp as "$label"?',
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(ctx, false),
              child: const Text('cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(ctx, true),
              child: const Text('yes, update'),
            ),
          ],
        ),
      );
      if (confirmed != true) return;
    }

    await _setRsvp(status, plusOneCount: plusOneCount);
  }

  Future<void> _removeRsvp() async {
    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.delete('/api/community/events/${widget.event.id}/rsvp/');
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
      _log.info('rsvp removed for event ${widget.event.id}');
    } catch (e, st) {
      _log.warning('failed to remove rsvp', e, st);
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t remove your rsvp — try again');
      }
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final liveEvent =
        ref.watch(eventDetailProvider(widget.event.id)).value ?? widget.event;
    final myRsvp = liveEvent.myRsvp;
    final guests = liveEvent.guests;

    final currentUser = ref.watch(authProvider).value;
    final isCoHost =
        currentUser != null &&
        (liveEvent.coHostIds.contains(currentUser.id) ||
            liveEvent.createdById == currentUser.id);

    final attendingCount = guests
        .where((g) => g.status == RsvpStatus.attending)
        .fold(0, (sum, g) => sum + 1 + g.plusOneCount);
    final maybeCount = guests
        .where((g) => g.status == RsvpStatus.maybe)
        .fold(0, (sum, g) => sum + 1 + g.plusOneCount);

    final summaryParts = [
      if (attendingCount > 0) '$attendingCount going',
      if (maybeCount > 0) '$maybeCount maybe',
    ];

    return Column(
      crossAxisAlignment: CrossAxisAlignment.center,
      children: [
        if (summaryParts.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(bottom: 10),
            child: Text(
              summaryParts.join(' · '),
              style: TextStyle(
                fontSize: 13,
                fontWeight: FontWeight.w500,
                color: cs.onSurfaceVariant,
              ),
              textAlign: TextAlign.center,
            ),
          ),
        Opacity(
          opacity: _loading ? 0.5 : 1.0,
          child: Row(
            spacing: 8,
            children: [
              Expanded(
                child: _RsvpToggleButton(
                  label: "i'm going",
                  icon: Icons.sentiment_very_satisfied_outlined,
                  activeColor: cs.primary,
                  isActive: myRsvp == RsvpStatus.attending,
                  enabled: !_loading,
                  onTap: () => myRsvp == RsvpStatus.attending
                      ? _removeRsvp()
                      : _setRsvp(RsvpStatus.attending),
                ),
              ),
              Expanded(
                child: _RsvpToggleButton(
                  label: 'maybe',
                  icon: Icons.sentiment_neutral_outlined,
                  activeColor: cs.tertiary,
                  isActive: myRsvp == RsvpStatus.maybe,
                  enabled: !_loading,
                  onTap: () => myRsvp == RsvpStatus.maybe
                      ? _removeRsvp()
                      : _confirmAndSetRsvp(RsvpStatus.maybe, 'maybe'),
                ),
              ),
              Expanded(
                child: _RsvpToggleButton(
                  label: "can't make it",
                  icon: Icons.sentiment_dissatisfied_outlined,
                  activeColor: cs.error,
                  isActive: myRsvp == RsvpStatus.cantGo,
                  enabled: !_loading,
                  onTap: () => myRsvp == RsvpStatus.cantGo
                      ? _removeRsvp()
                      : _confirmAndSetRsvp(RsvpStatus.cantGo, "can't make it"),
                ),
              ),
            ],
          ),
        ),
        if (liveEvent.allowPlusOnes &&
            (myRsvp == RsvpStatus.attending || myRsvp == RsvpStatus.maybe)) ...[
          const SizedBox(height: 12),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Text(
                'bringing +1s',
                style: TextStyle(fontSize: 13, color: cs.onSurfaceVariant),
              ),
              const SizedBox(width: 12),
              IconButton(
                icon: const Icon(Icons.remove, size: 18),
                tooltip: 'remove a +1',
                onPressed: _plusOneCount > 0
                    ? () {
                        setState(() => _plusOneCount--);
                        _setRsvp(myRsvp!, plusOneCount: _plusOneCount);
                      }
                    : null,
              ),
              Text('$_plusOneCount', style: const TextStyle(fontSize: 15)),
              IconButton(
                icon: const Icon(Icons.add, size: 18),
                tooltip: 'add a +1',
                onPressed: () {
                  setState(() => _plusOneCount++);
                  _setRsvp(myRsvp!, plusOneCount: _plusOneCount);
                },
              ),
            ],
          ),
        ],
        if (guests.isNotEmpty || liveEvent.invitedUserNames.isNotEmpty) ...[
          const SizedBox(height: 16),
          RsvpGuestList(
            guests: guests,
            invitedUserIds: liveEvent.invitedUserIds,
            invitedUserNames: liveEvent.invitedUserNames,
            invitedUserPhotoUrls: liveEvent.invitedUserPhotoUrls,
            showInvited: isCoHost,
          ),
        ],
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Toggle button
// ---------------------------------------------------------------------------

class _RsvpToggleButton extends StatelessWidget {
  final String label;
  final IconData icon;
  final Color activeColor;
  final bool isActive;
  final bool enabled;
  final VoidCallback onTap;

  const _RsvpToggleButton({
    required this.label,
    required this.icon,
    required this.activeColor,
    required this.isActive,
    required this.enabled,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Semantics(
      button: true,
      label: 'rsvp $label${isActive ? ", selected" : ""}',
      excludeSemantics: true,
      child: InkWell(
        onTap: enabled ? onTap : null,
        borderRadius: BorderRadius.circular(24),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 200),
          alignment: Alignment.center,
          padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 8),
          decoration: BoxDecoration(
            color: isActive
                ? activeColor.withValues(alpha: 0.15)
                : Colors.transparent,
            borderRadius: BorderRadius.circular(24),
            border: Border.all(
              color: isActive ? activeColor : cs.outlineVariant,
              width: isActive ? 2 : 1,
            ),
          ),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                icon,
                size: 18,
                color: isActive ? activeColor : cs.onSurfaceVariant,
              ),
              const SizedBox(height: 4),
              Text(
                label,
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: isActive ? FontWeight.w700 : FontWeight.w500,
                  color: isActive ? activeColor : cs.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
