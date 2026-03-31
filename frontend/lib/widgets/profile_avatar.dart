import 'package:flutter/material.dart';

/// Small circular profile photo, used in the bottom nav bar and elsewhere.
class ProfileAvatar extends StatelessWidget {
  final String photoUrl;
  final double radius;
  final bool selected;

  const ProfileAvatar({
    super.key,
    required this.photoUrl,
    this.radius = 14,
    this.selected = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration:
          selected
              ? BoxDecoration(
                shape: BoxShape.circle,
                border: Border.all(color: theme.colorScheme.primary, width: 2),
              )
              : null,
      child: CircleAvatar(
        radius: radius,
        backgroundImage: NetworkImage(photoUrl),
        backgroundColor: theme.colorScheme.surfaceContainerHighest,
      ),
    );
  }
}
