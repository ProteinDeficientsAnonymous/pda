import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/event.dart';
import 'package:pda/screens/calendar/guest_avatars.dart';

class GuestChip extends StatefulWidget {
  final EventGuest guest;

  const GuestChip({super.key, required this.guest});

  @override
  State<GuestChip> createState() => _GuestChipState();
}

class _GuestChipState extends State<GuestChip> {
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
      builder: (_) => GestureDetector(
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
                color: Theme.of(context).colorScheme.inverseSurface,
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
                        color: Theme.of(context).colorScheme.onInverseSurface,
                      ),
                      const SizedBox(width: 6),
                      SelectableText(
                        phone,
                        style: TextStyle(
                          fontSize: 13,
                          fontFamily: 'monospace',
                          color: Theme.of(context).colorScheme.onInverseSurface,
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
    final cs = Theme.of(context).colorScheme;

    if (phone == null) {
      return Semantics(
        button: true,
        label: "view ${widget.guest.name}'s profile",
        excludeSemantics: true,
        child: InkWell(
          onTap: () => context.push('/members/${widget.guest.userId}'),
          customBorder: const StadiumBorder(),
          child: Padding(
            padding: const EdgeInsets.all(2),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                GuestAvatar(guest: widget.guest),
                const SizedBox(width: 6),
                Text(widget.guest.name, style: const TextStyle(fontSize: 13)),
                if (widget.guest.hasPlusOne) ...[
                  const SizedBox(width: 4),
                  Text(
                    '+ 1',
                    style: TextStyle(fontSize: 11, color: cs.onSurfaceVariant),
                  ),
                ],
              ],
            ),
          ),
        ),
      );
    }

    if (isWide) {
      return Semantics(
        button: true,
        label: "view ${widget.guest.name}'s profile",
        excludeSemantics: true,
        child: CompositedTransformTarget(
          link: _link,
          child: MouseRegion(
            onEnter: (_) => _showOverlay(phone),
            onExit: (_) => _removeOverlay(),
            cursor: SystemMouseCursors.basic,
            child: InkWell(
              onTap: () => context.push('/members/${widget.guest.userId}'),
              customBorder: const StadiumBorder(),
              child: Padding(
                padding: const EdgeInsets.all(2),
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    GuestAvatar(guest: widget.guest),
                    const SizedBox(width: 6),
                    Text(
                      widget.guest.name,
                      style: const TextStyle(fontSize: 13),
                    ),
                    if (widget.guest.hasPlusOne) ...[
                      const SizedBox(width: 4),
                      Text(
                        '+ 1',
                        style: TextStyle(
                          fontSize: 11,
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ),
          ),
        ),
      );
    }

    // Mobile: tap navigates to profile, phone shown as subtitle
    return Semantics(
      button: true,
      label: "view ${widget.guest.name}'s profile",
      excludeSemantics: true,
      child: InkWell(
        onTap: () => context.push('/members/${widget.guest.userId}'),
        customBorder: const StadiumBorder(),
        child: Padding(
          padding: const EdgeInsets.all(2),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              GuestAvatar(guest: widget.guest),
              const SizedBox(width: 6),
              Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(widget.guest.name, style: const TextStyle(fontSize: 13)),
                  Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      Icon(
                        Icons.smartphone_outlined,
                        size: 11,
                        color: cs.onSurfaceVariant,
                      ),
                      const SizedBox(width: 3),
                      Text(
                        phone,
                        style: TextStyle(
                          fontSize: 11,
                          fontFamily: 'monospace',
                          color: cs.onSurfaceVariant,
                        ),
                      ),
                      if (widget.guest.hasPlusOne) ...[
                        const SizedBox(width: 6),
                        Text(
                          '+ 1',
                          style: TextStyle(
                            fontSize: 11,
                            color: cs.onSurfaceVariant,
                          ),
                        ),
                      ],
                    ],
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}
