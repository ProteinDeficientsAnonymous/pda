import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'role_form_dialog.dart';

class RolesTab extends ConsumerWidget {
  final bool canManageRoles;

  const RolesTab({super.key, required this.canManageRoles});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rolesAsync = ref.watch(rolesProvider);

    return rolesAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error:
          (e, _) => const Center(
            child: Text('couldn\'t load roles — try refreshing'),
          ),
      data: (roles) {
        return Column(
          children: [
            if (canManageRoles)
              Padding(
                padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
                child: Align(
                  alignment: Alignment.centerRight,
                  child: FilledButton.icon(
                    onPressed: () => _showCreateRoleDialog(context, ref),
                    icon: const Icon(Icons.add_circle_outline, size: 18),
                    label: const Text('New role'),
                  ),
                ),
              ),
            Expanded(
              child: ListView.separated(
                padding: const EdgeInsets.all(24),
                itemCount: roles.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder:
                    (context, index) => RoleCard(
                      role: roles[index],
                      canManageRoles: canManageRoles,
                    ),
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _showCreateRoleDialog(
    BuildContext context,
    WidgetRef ref,
  ) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const RoleFormDialog(),
    );
    if (result == null) return;

    try {
      await ref
          .read(userManagementProvider.notifier)
          .createRole(
            result['name'] as String,
            List<String>.from(result['permissions'] as List),
          );
      if (context.mounted) {
        showSnackBar(context, 'Role created');
      }
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }
}

class RoleCard extends ConsumerWidget {
  final Role role;
  final bool canManageRoles;

  const RoleCard({super.key, required this.role, required this.canManageRoles});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(userManagementProvider.notifier);
    final theme = Theme.of(context);

    return Card(
      elevation: 2,
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Row(
                    children: [
                      Text(role.name, style: theme.textTheme.titleMedium),
                      if (role.isDefault) ...[
                        const SizedBox(width: 8),
                        Container(
                          padding: const EdgeInsets.symmetric(
                            horizontal: 6,
                            vertical: 2,
                          ),
                          decoration: BoxDecoration(
                            color: theme.colorScheme.surfaceContainerHighest,
                            borderRadius: BorderRadius.circular(4),
                          ),
                          child: Text(
                            'built-in',
                            style: TextStyle(
                              fontSize: 10,
                              color: theme.colorScheme.onSurfaceVariant,
                            ),
                          ),
                        ),
                      ],
                    ],
                  ),
                ),
                if (canManageRoles && !role.isDefault) ...[
                  IconButton(
                    icon: const Icon(Icons.edit_outlined, size: 18),
                    tooltip: 'Edit permissions',
                    onPressed: () => _showEditDialog(context, notifier),
                  ),
                  IconButton(
                    icon: Icon(
                      Icons.delete_outline,
                      size: 18,
                      color: theme.colorScheme.error,
                    ),
                    tooltip: 'Delete role',
                    onPressed: () => _confirmDelete(context, notifier),
                  ),
                ],
              ],
            ),
            if (role.permissions.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children:
                    role.permissions
                        .map((p) => PermissionChip(permission: p))
                        .toList(),
              ),
            ] else ...[
              const SizedBox(height: 4),
              Text(
                'No permissions',
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  Future<void> _showEditDialog(
    BuildContext context,
    UserManagementNotifier notifier,
  ) async {
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => RoleFormDialog(role: role),
    );
    if (result == null) return;

    try {
      await notifier.updateRole(
        role.id,
        List<String>.from(result['permissions'] as List),
      );
      if (context.mounted) {
        showSnackBar(context, 'Role updated');
      }
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  Future<void> _confirmDelete(
    BuildContext context,
    UserManagementNotifier notifier,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Delete role?'),
            content: Text(
              'Delete the "${role.name}" role? Users with this role will lose its permissions.',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(ctx).pop(false),
                child: const Text('Cancel'),
              ),
              TextButton(
                style: TextButton.styleFrom(
                  foregroundColor: Theme.of(ctx).colorScheme.error,
                ),
                onPressed: () => Navigator.of(ctx).pop(true),
                child: const Text('Delete'),
              ),
            ],
          ),
    );
    if (confirmed != true) return;

    try {
      await notifier.deleteRole(role.id);
      if (context.mounted) {
        showSnackBar(context, '"${role.name}" deleted');
      }
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }
}

class PermissionChip extends StatelessWidget {
  final String permission;

  const PermissionChip({super.key, required this.permission});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        kPermissionLabels[permission] ?? permission,
        style: TextStyle(
          fontSize: 11,
          color: Theme.of(context).colorScheme.onPrimaryContainer,
        ),
      ),
    );
  }
}
