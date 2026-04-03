import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/profile_avatar.dart';

class ProfileScreen extends ConsumerWidget {
  const ProfileScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).value;
    final theme = Theme.of(context);

    return AppScaffold(
      maxWidth: 600,
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          if (user != null) ...[
            Center(
              child: ProfileAvatar(photoUrl: user.profilePhotoUrl, radius: 48),
            ),
            const SizedBox(height: 16),
            Center(
              child: Text(
                user.displayName.isNotEmpty
                    ? user.displayName
                    : user.phoneNumber,
                style: theme.textTheme.titleLarge?.copyWith(
                  fontWeight: FontWeight.w600,
                ),
              ),
            ),
            const SizedBox(height: 24),
            _InfoTile(
              icon: Icons.phone_outlined,
              label: 'phone',
              value: user.phoneNumber,
              visible: user.showPhone,
            ),
            if (user.email.isNotEmpty) ...[
              const SizedBox(height: 8),
              _InfoTile(
                icon: Icons.email_outlined,
                label: 'email',
                value: user.email,
                visible: user.showEmail,
              ),
            ],
            const SizedBox(height: 24),
            _ProfileButton(
              icon: Icons.tune_outlined,
              label: 'settings',
              onTap: () => context.go('/settings'),
            ),
            const SizedBox(height: 8),
            _ProfileButton(
              icon: Icons.event_outlined,
              label: 'my events',
              onTap: () => context.go('/events/mine'),
            ),
            if (user.hasAnyAdminPermission) ...[
              const SizedBox(height: 8),
              _ProfileButton(
                icon: Icons.admin_panel_settings_outlined,
                label: 'admin',
                onTap: () => context.go('/admin'),
              ),
            ],
            const SizedBox(height: 24),
            _ProfileButton(
              icon: Icons.logout_outlined,
              label: 'log out',
              isDestructive: true,
              onTap: () async {
                await ref.read(authProvider.notifier).logout();
                if (context.mounted) {
                  context.go('/');
                  showSnackBar(context, 'you\'re logged out');
                }
              },
            ),
          ] else ...[
            _ProfileButton(
              icon: Icons.login_outlined,
              label: 'log in',
              onTap: () => context.go('/login'),
            ),
          ],
        ],
      ),
    );
  }
}

class _InfoTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String value;
  final bool visible;

  const _InfoTile({
    required this.icon,
    required this.label,
    required this.value,
    required this.visible,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.15),
        ),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: theme.colorScheme.onSurfaceVariant),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  label,
                  style: TextStyle(
                    fontSize: 11,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                  ),
                ),
                const SizedBox(height: 2),
                Text(value, style: const TextStyle(fontSize: 15)),
              ],
            ),
          ),
          IconButton(
            icon: const Icon(Icons.content_copy_outlined, size: 16),
            tooltip: 'copy',
            onPressed: () {
              Clipboard.setData(ClipboardData(text: value));
              showSnackBar(context, 'copied ✓');
            },
          ),
          const SizedBox(width: 4),
          Tooltip(
            message: visible ? 'visible to members' : 'hidden from members',
            child: Icon(
              visible
                  ? Icons.visibility_outlined
                  : Icons.visibility_off_outlined,
              size: 16,
              color: visible
                  ? theme.colorScheme.primary.withValues(alpha: 0.7)
                  : theme.colorScheme.onSurface.withValues(alpha: 0.3),
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileButton extends StatelessWidget {
  final IconData icon;
  final String label;
  final VoidCallback onTap;
  final bool isDestructive;

  const _ProfileButton({
    required this.icon,
    required this.label,
    required this.onTap,
    this.isDestructive = false,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final color = isDestructive
        ? theme.colorScheme.error
        : theme.colorScheme.onSurface;

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 14),
        decoration: BoxDecoration(
          color: theme.colorScheme.surfaceContainerLow,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(
            color: isDestructive
                ? theme.colorScheme.error.withValues(alpha: 0.3)
                : theme.colorScheme.outline.withValues(alpha: 0.15),
          ),
        ),
        child: Row(
          children: [
            Icon(icon, size: 20, color: color),
            const SizedBox(width: 16),
            Expanded(
              child: Text(
                label,
                style: TextStyle(
                  fontSize: 15,
                  fontWeight: FontWeight.w500,
                  color: color,
                ),
              ),
            ),
            if (!isDestructive)
              Icon(
                Icons.chevron_right,
                size: 20,
                color: theme.colorScheme.onSurface.withValues(alpha: 0.3),
              ),
          ],
        ),
      ),
    );
  }
}
