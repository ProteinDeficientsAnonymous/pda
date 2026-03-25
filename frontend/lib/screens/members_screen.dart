import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

// TODO: Restrict this screen to users with the `manage_users` permission once
// the User model includes a `roles` field. For now any authenticated user can
// access it (the route already requires auth).

class MembersScreen extends ConsumerWidget {
  const MembersScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usersAsync = ref.watch(usersProvider);

    return AppScaffold(
      title: 'Members',
      child: usersAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) => Center(child: Text('Failed to load members: $e')),
        data: (users) {
          if (users.isEmpty) {
            return const Center(
              child: Padding(
                padding: EdgeInsets.all(32),
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Icon(Icons.people_outline, size: 64, color: Colors.grey),
                    SizedBox(height: 16),
                    Text(
                      'No members found',
                      style: TextStyle(fontSize: 18, color: Colors.grey),
                    ),
                  ],
                ),
              ),
            );
          }

          return ListView.separated(
            padding: const EdgeInsets.all(24),
            itemCount: users.length,
            separatorBuilder: (_, __) => const SizedBox(height: 12),
            itemBuilder: (context, index) => _MemberRow(user: users[index]),
          );
        },
      ),
    );
  }
}

class _MemberRow extends ConsumerWidget {
  final User user;

  const _MemberRow({required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(userManagementProvider.notifier);

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '${user.firstName} ${user.lastName}'.trim().isNotEmpty
                        ? '${user.firstName} ${user.lastName}'.trim()
                        : '(no name)',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  Text(user.email, style: const TextStyle(color: Colors.grey)),
                ],
              ),
            ),
            OutlinedButton.icon(
              icon: const Icon(Icons.lock_reset, size: 18),
              label: const Text('Reset password'),
              onPressed: () => _handleResetPassword(context, notifier),
            ),
            const SizedBox(width: 8),
            OutlinedButton.icon(
              icon: const Icon(Icons.delete_outline, size: 18, color: Colors.red),
              label: const Text('Delete', style: TextStyle(color: Colors.red)),
              style: OutlinedButton.styleFrom(
                side: const BorderSide(color: Colors.red),
              ),
              onPressed: () => _handleDelete(context, notifier),
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _handleResetPassword(
    BuildContext context,
    UserManagementNotifier notifier,
  ) async {
    try {
      final tempPassword = await notifier.resetPassword(user.id);
      if (!context.mounted) return;
      _showTempPasswordDialog(context, tempPassword);
    } catch (e) {
      if (!context.mounted) return;
      _showErrorSnackbar(context, 'Failed to reset password: $e');
    }
  }

  Future<void> _handleDelete(
    BuildContext context,
    UserManagementNotifier notifier,
  ) async {
    final confirmed = await _showDeleteConfirmDialog(context);
    if (!confirmed) return;
    if (!context.mounted) return;
    try {
      await notifier.deleteUser(user.id);
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text('${user.email} has been deleted.')),
      );
    } catch (e) {
      if (!context.mounted) return;
      _showErrorSnackbar(context, 'Failed to delete user: $e');
    }
  }

  Future<bool> _showDeleteConfirmDialog(BuildContext context) async {
    final result = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete member?'),
        content: Text(
          'Are you sure you want to delete ${user.email}? This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(false),
            child: const Text('Cancel'),
          ),
          TextButton(
            style: TextButton.styleFrom(foregroundColor: Colors.red),
            onPressed: () => Navigator.of(ctx).pop(true),
            child: const Text('Delete'),
          ),
        ],
      ),
    );
    return result ?? false;
  }

  void _showTempPasswordDialog(BuildContext context, String tempPassword) {
    showDialog<void>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Temporary password'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('A temporary password has been set for ${user.email}:'),
            const SizedBox(height: 12),
            SelectableText(
              tempPassword,
              style: const TextStyle(
                fontFamily: 'monospace',
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
            ),
            const SizedBox(height: 8),
            const Text(
              'Share this with the member — they should change it on next login.',
              style: TextStyle(color: Colors.grey, fontSize: 13),
            ),
          ],
        ),
        actions: [
          TextButton(
            onPressed: () {
              Clipboard.setData(ClipboardData(text: tempPassword));
              ScaffoldMessenger.of(context).showSnackBar(
                const SnackBar(content: Text('Copied to clipboard')),
              );
            },
            child: const Text('Copy'),
          ),
          TextButton(
            onPressed: () => Navigator.of(ctx).pop(),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  void _showErrorSnackbar(BuildContext context, String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: Colors.red,
      ),
    );
  }
}
