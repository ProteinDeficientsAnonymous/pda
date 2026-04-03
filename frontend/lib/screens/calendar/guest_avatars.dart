import 'package:flutter/material.dart';
import 'package:pda/models/event.dart';

class StackedAvatarRow extends StatelessWidget {
  final List<EventGuest> guests;
  static const int _maxVisible = 5;
  static const double _radius = 14;
  static const double _overlap = _radius * 1.2;

  const StackedAvatarRow({super.key, required this.guests});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final visible = guests.take(_maxVisible).toList();
    final overflow = guests.length - _maxVisible;
    final stackWidth = visible.isEmpty
        ? 0.0
        : _radius * 2 + (visible.length - 1) * _overlap;

    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        SizedBox(
          width: stackWidth,
          height: _radius * 2,
          child: Stack(
            children: [
              for (var i = visible.length - 1; i >= 0; i--)
                Positioned(
                  left: i * _overlap,
                  child: StackedAvatar(
                    guest: visible[i],
                    radius: _radius,
                    borderColor: cs.surface,
                  ),
                ),
            ],
          ),
        ),
        if (overflow > 0) ...[
          const SizedBox(width: 6),
          Text(
            '+$overflow',
            style: TextStyle(
              fontSize: 12,
              color: cs.onSurfaceVariant,
              fontWeight: FontWeight.w500,
            ),
          ),
        ],
      ],
    );
  }
}

class StackedAvatar extends StatelessWidget {
  final EventGuest guest;
  final double radius;
  final Color borderColor;

  const StackedAvatar({
    super.key,
    required this.guest,
    required this.radius,
    required this.borderColor,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final initials = guest.name.isNotEmpty ? guest.name[0].toUpperCase() : '?';

    return Container(
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        border: Border.all(color: borderColor, width: 2),
      ),
      child: CircleAvatar(
        radius: radius - 2,
        backgroundImage: guest.photoUrl.isNotEmpty
            ? NetworkImage(guest.photoUrl)
            : null,
        backgroundColor: cs.primaryContainer,
        child: guest.photoUrl.isEmpty
            ? Text(
                initials,
                style: TextStyle(
                  fontSize: (radius - 2) * 0.85,
                  fontWeight: FontWeight.w600,
                  color: cs.onPrimaryContainer,
                ),
              )
            : null,
      ),
    );
  }
}

class GuestAvatar extends StatelessWidget {
  final EventGuest guest;

  const GuestAvatar({super.key, required this.guest});

  static const double radius = 14;

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final initials = guest.name.isNotEmpty ? guest.name[0].toUpperCase() : '?';

    if (guest.photoUrl.isNotEmpty) {
      return CircleAvatar(
        radius: radius,
        backgroundImage: NetworkImage(guest.photoUrl),
      );
    }
    return CircleAvatar(
      radius: radius,
      backgroundColor: cs.primaryContainer,
      child: Text(
        initials,
        style: TextStyle(
          fontSize: radius * 0.9,
          fontWeight: FontWeight.w600,
          color: cs.onPrimaryContainer,
        ),
      ),
    );
  }
}
