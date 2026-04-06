import 'package:flutter/material.dart';
import 'package:pda/models/event.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/screens/calendar/guest_chip.dart';

class RsvpGuestList extends StatefulWidget {
  final List<EventGuest> guests;
  final List<String> invitedUserIds;
  final List<String> invitedUserNames;
  final List<String> invitedUserPhotoUrls;
  final bool showInvited;

  const RsvpGuestList({
    super.key,
    required this.guests,
    this.invitedUserIds = const [],
    this.invitedUserNames = const [],
    this.invitedUserPhotoUrls = const [],
    this.showInvited = false,
  });

  @override
  State<RsvpGuestList> createState() => _RsvpGuestListState();
}

class _RsvpGuestListState extends State<RsvpGuestList> {
  late String _selected;

  @override
  void initState() {
    super.initState();
    _selected = _defaultTab();
  }

  @override
  void didUpdateWidget(RsvpGuestList old) {
    super.didUpdateWidget(old);
    // If the selected tab becomes empty after a data update, pick a new default.
    if (_currentGuests().isEmpty && _invitedGuests().isEmpty) return;
    if (_selected == _kInvited && !widget.showInvited) {
      _selected = _defaultTab();
    } else if (_tabCount(_selected) == 0) {
      _selected = _defaultTab();
    }
  }

  static const _kGoing = RsvpStatus.attending;
  static const _kMaybe = RsvpStatus.maybe;
  static const _kCantGo = RsvpStatus.cantGo;
  static const _kInvited = 'invited';

  String _defaultTab() {
    if (_tabCount(_kGoing) > 0) return _kGoing;
    if (_tabCount(_kMaybe) > 0) return _kMaybe;
    if (_tabCount(_kCantGo) > 0) return _kCantGo;
    if (widget.showInvited && widget.invitedUserNames.isNotEmpty) {
      return _kInvited;
    }
    return _kGoing;
  }

  int _tabCount(String tab) {
    if (tab == _kInvited) return widget.invitedUserNames.length;
    return widget.guests.where((g) => g.status == tab).length;
  }

  List<EventGuest> _currentGuests() =>
      widget.guests.where((g) => g.status == _selected).toList();

  List<EventGuest> _invitedGuests() {
    if (_selected != _kInvited) return [];
    return [
      for (var i = 0; i < widget.invitedUserNames.length; i++)
        EventGuest(
          userId: i < widget.invitedUserIds.length
              ? widget.invitedUserIds[i]
              : '',
          name: widget.invitedUserNames[i],
          status: _kInvited,
          photoUrl: i < widget.invitedUserPhotoUrls.length
              ? widget.invitedUserPhotoUrls[i]
              : '',
        ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    final tabs = [
      (_kGoing, 'going'),
      (_kMaybe, 'maybe'),
      (_kCantGo, "can't"),
      if (widget.showInvited) (_kInvited, 'invited'),
    ];

    final displayGuests = _selected == _kInvited
        ? _invitedGuests()
        : _currentGuests();

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            spacing: 8,
            children: [
              for (final (key, label) in tabs)
                _TabChip(
                  label: '$label (${_tabCount(key)})',
                  selected: _selected == key,
                  onTap: () => setState(() => _selected = key),
                ),
            ],
          ),
        ),
        if (displayGuests.isNotEmpty) ...[
          const SizedBox(height: 10),
          Wrap(
            spacing: 8,
            runSpacing: 6,
            children: displayGuests.map((g) => GuestChip(guest: g)).toList(),
          ),
        ],
      ],
    );
  }
}

class _TabChip extends StatelessWidget {
  final String label;
  final bool selected;
  final VoidCallback onTap;

  const _TabChip({
    required this.label,
    required this.selected,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Semantics(
      button: true,
      selected: selected,
      label: label,
      excludeSemantics: true,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(20),
        child: AnimatedContainer(
          duration: const Duration(milliseconds: 150),
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: selected
                ? cs.primaryContainer
                : cs.surfaceContainerHighest.withValues(alpha: 0.5),
            borderRadius: BorderRadius.circular(20),
            border: Border.all(
              color: selected ? cs.primary : cs.outlineVariant,
              width: selected ? 1.5 : 1,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 12,
              fontWeight: selected ? FontWeight.w700 : FontWeight.w500,
              color: selected ? cs.onPrimaryContainer : cs.onSurfaceVariant,
            ),
          ),
        ),
      ),
    );
  }
}
