import 'package:flutter/material.dart';
import 'package:pda/models/event.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/screens/calendar/guest_avatars.dart';
import 'package:pda/screens/calendar/guest_chip.dart';

class RsvpGuestList extends StatelessWidget {
  final List<EventGuest> guests;

  const RsvpGuestList({super.key, required this.guests});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final attending = guests
        .where((g) => g.status == RsvpStatus.attending)
        .toList();
    final maybe = guests.where((g) => g.status == RsvpStatus.maybe).toList();
    final cantGo = guests.where((g) => g.status == RsvpStatus.cantGo).toList();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        GuestStatusGroup(label: 'going', guests: attending, color: cs.primary),
        GuestStatusGroup(label: 'maybe', guests: maybe, color: cs.tertiary),
        GuestStatusGroup(
          label: "can't make it",
          guests: cantGo,
          color: cs.error,
        ),
      ],
    );
  }
}

class GuestStatusGroup extends StatefulWidget {
  final String label;
  final List<EventGuest> guests;
  final Color color;

  const GuestStatusGroup({
    super.key,
    required this.label,
    required this.guests,
    required this.color,
  });

  @override
  State<GuestStatusGroup> createState() => _GuestStatusGroupState();
}

class _GuestStatusGroupState extends State<GuestStatusGroup> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    if (widget.guests.isEmpty) return const SizedBox.shrink();
    final cs = Theme.of(context).colorScheme;
    final count = widget.guests.length;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Semantics(
            button: true,
            label:
                '$count ${widget.label}, tap to ${_expanded ? 'collapse' : 'expand'} guest list',
            excludeSemantics: true,
            child: InkWell(
              onTap: () => setState(() => _expanded = !_expanded),
              borderRadius: BorderRadius.circular(8),
              child: Padding(
                padding: const EdgeInsets.symmetric(vertical: 6),
                child: Row(
                  children: [
                    StackedAvatarRow(guests: widget.guests),
                    const SizedBox(width: 10),
                    Text(
                      '$count ${widget.label}',
                      style: TextStyle(
                        fontSize: 13,
                        fontWeight: FontWeight.w600,
                        color: widget.color,
                      ),
                    ),
                    const Spacer(),
                    Icon(
                      _expanded
                          ? Icons.expand_less_rounded
                          : Icons.expand_more_rounded,
                      size: 18,
                      color: cs.onSurfaceVariant,
                    ),
                  ],
                ),
              ),
            ),
          ),
          AnimatedSize(
            duration: const Duration(milliseconds: 250),
            curve: Curves.easeInOut,
            child: _expanded
                ? Padding(
                    padding: const EdgeInsets.only(top: 4, left: 4),
                    child: Wrap(
                      spacing: 8,
                      runSpacing: 6,
                      children: widget.guests
                          .map((g) => GuestChip(guest: g))
                          .toList(),
                    ),
                  )
                : const SizedBox.shrink(),
          ),
        ],
      ),
    );
  }
}
