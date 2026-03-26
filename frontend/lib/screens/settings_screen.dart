import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;

    return AppScaffold(
      title: 'Settings',
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          // Profile photo
          Center(
            child: Stack(
              children: [
                CircleAvatar(
                  radius: 48,
                  backgroundColor:
                      Theme.of(context).colorScheme.primaryContainer,
                  child: Text(
                    _initials(user?.displayName, user?.email),
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
                Positioned(
                  bottom: 0,
                  right: 0,
                  child: Tooltip(
                    message: 'Coming soon',
                    child: CircleAvatar(
                      radius: 16,
                      backgroundColor: Theme.of(context).colorScheme.surface,
                      child: Icon(
                        Icons.camera_alt_outlined,
                        size: 16,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          Text(
            'Profile',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          _SettingsTile(
            icon: Icons.person_outline,
            label: 'Name',
            value:
                (user?.displayName ?? '').trim().isEmpty
                    ? 'Not set'
                    : user!.displayName,
            onTap: () => _showComingSoon(context),
          ),
          _SettingsTile(
            icon: Icons.email_outlined,
            label: 'Email',
            value: user?.email ?? '',
            onTap: () => _showComingSoon(context),
          ),
          const SizedBox(height: 24),
          Text(
            'Security',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          _SettingsTile(
            icon: Icons.lock_outline,
            label: 'Change password',
            onTap: () => _showComingSoon(context),
          ),
        ],
      ),
    );
  }

  String _initials(String? displayName, String? email) {
    if (displayName != null && displayName.isNotEmpty) {
      final parts = displayName.trim().split(RegExp(r'\s+'));
      final f = parts.first[0].toUpperCase();
      final l = parts.length > 1 ? parts.last[0].toUpperCase() : '';
      return '$f$l';
    }
    if (email != null && email.isNotEmpty) return email[0].toUpperCase();
    return '?';
  }

  void _showComingSoon(BuildContext context) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Coming soon')));
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback onTap;

  const _SettingsTile({
    required this.icon,
    required this.label,
    required this.onTap,
    this.value,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          icon,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        title: Text(label),
        subtitle: value != null ? Text(value!) : null,
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
