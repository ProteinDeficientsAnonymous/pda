import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl_phone_field/intl_phone_field.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/app_scaffold.dart';

// All permission keys and their display labels
const _kPermissionLabels = {
  'create_user': 'Create user',
  'manage_users': 'Manage users',
  'manage_roles': 'Manage roles',
  'approve_join_requests': 'Approve join requests',
  'manage_events': 'Manage events',
};

class MembersScreen extends ConsumerStatefulWidget {
  const MembersScreen({super.key});

  @override
  ConsumerState<MembersScreen> createState() => _MembersScreenState();
}

class _MembersScreenState extends ConsumerState<MembersScreen>
    with SingleTickerProviderStateMixin {
  late final TabController _tabController;

  @override
  void initState() {
    super.initState();
    _tabController = TabController(length: 2, vsync: this);
  }

  @override
  void dispose() {
    _tabController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final currentUser = ref.watch(authProvider).valueOrNull;
    final canManageRoles = currentUser?.hasPermission('manage_roles') ?? false;
    final canManageUsers = currentUser?.hasPermission('manage_users') ?? false;

    return AppScaffold(
      child: Column(
        children: [
          TabBar(
            controller: _tabController,
            tabs: const [Tab(text: 'Members'), Tab(text: 'Roles')],
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                _MembersTab(
                  canManageRoles: canManageRoles,
                  canManageUsers: canManageUsers,
                ),
                _RolesTab(canManageRoles: canManageRoles),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Members tab
// ---------------------------------------------------------------------------

class _MembersTab extends ConsumerWidget {
  final bool canManageRoles;
  final bool canManageUsers;

  const _MembersTab({
    required this.canManageRoles,
    required this.canManageUsers,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final usersAsync = ref.watch(usersProvider);
    final rolesAsync = ref.watch(rolesProvider);

    return Column(
      children: [
        if (canManageUsers)
          Padding(
            padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.end,
              children: [
                OutlinedButton.icon(
                  onPressed: () => _showBulkAddDialog(context, ref),
                  icon: const Icon(Icons.group_add, size: 18),
                  label: const Text('Bulk add'),
                ),
                const SizedBox(width: 8),
                FilledButton.icon(
                  onPressed: () => _showAddMemberDialog(context, ref),
                  icon: const Icon(Icons.person_add, size: 18),
                  label: const Text('Add member'),
                ),
              ],
            ),
          ),
        Expanded(
          child: usersAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('Failed to load members: $e')),
            data: (users) {
              if (users.isEmpty) {
                return const Center(
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
                );
              }
              final allRoles = rolesAsync.valueOrNull ?? [];
              return ListView.separated(
                padding: const EdgeInsets.all(24),
                itemCount: users.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder:
                    (context, index) => _MemberCard(
                      user: users[index],
                      allRoles: allRoles,
                      canManageRoles: canManageRoles,
                    ),
              );
            },
          ),
        ),
      ],
    );
  }

  Future<void> _showAddMemberDialog(BuildContext context, WidgetRef ref) async {
    final rolesAsync = ref.read(rolesProvider);
    final allRoles = rolesAsync.valueOrNull ?? [];
    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => _AddMemberDialog(allRoles: allRoles),
    );
    if (result == null || !context.mounted) return;
    try {
      final data = await ref
          .read(userManagementProvider.notifier)
          .createUser(
            phoneNumber: result['phone_number'] as String,
            displayName: result['display_name'] as String? ?? '',
            email: result['email'] as String? ?? '',
            roleId: result['role_id'] as String?,
          );
      if (!context.mounted) return;
      _showCreatedPasswordDialog(
        context,
        displayName:
            data['display_name'] as String? ?? data['phone_number'] as String,
        tempPassword: data['temporary_password'] as String,
      );
    } catch (e) {
      if (!context.mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text(ApiError.from(e).message),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  void _showCreatedPasswordDialog(
    BuildContext context, {
    required String displayName,
    required String tempPassword,
  }) {
    showDialog<void>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Member created'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$displayName has been added. Share their temporary password:',
                ),
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
                  'They should change it on first login.',
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

  Future<void> _showBulkAddDialog(BuildContext context, WidgetRef ref) async {
    await showDialog<void>(
      context: context,
      builder: (_) => _BulkAddDialog(ref: ref),
    );
  }
}

class _MemberCard extends ConsumerWidget {
  final User user;
  final List<Role> allRoles;
  final bool canManageRoles;

  const _MemberCard({
    required this.user,
    required this.allRoles,
    required this.canManageRoles,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final notifier = ref.read(userManagementProvider.notifier);
    final currentUser = ref.watch(authProvider).valueOrNull;
    final isOwnAccount = currentUser?.id == user.id;

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
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.displayName.isNotEmpty
                            ? user.displayName
                            : '(no name)',
                        style: Theme.of(context).textTheme.titleMedium,
                      ),
                      const SizedBox(height: 2),
                      Text(
                        user.email.isNotEmpty ? user.email : user.phoneNumber,
                        style: const TextStyle(color: Colors.grey),
                      ),
                    ],
                  ),
                ),
                if (user.isSuperuser)
                  Chip(
                    label: const Text('Superuser'),
                    backgroundColor:
                        Theme.of(context).colorScheme.errorContainer,
                    labelStyle: TextStyle(
                      color: Theme.of(context).colorScheme.onErrorContainer,
                      fontSize: 11,
                    ),
                  ),
              ],
            ),
            // Role badges
            if (user.roles.isNotEmpty) ...[
              const SizedBox(height: 8),
              Wrap(
                spacing: 6,
                runSpacing: 4,
                children: user.roles.map((r) => _RoleBadge(role: r)).toList(),
              ),
            ],
            const SizedBox(height: 12),
            // Actions row
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: [
                if (canManageRoles)
                  OutlinedButton.icon(
                    icon: const Icon(Icons.shield_outlined, size: 16),
                    label: const Text('Edit roles'),
                    onPressed:
                        () => _showRoleEditor(
                          context,
                          ref,
                          notifier,
                          isOwnAccount,
                        ),
                  ),
                OutlinedButton.icon(
                  icon: const Icon(Icons.lock_reset, size: 16),
                  label: const Text('Reset password'),
                  onPressed: () => _handleResetPassword(context, notifier),
                ),
                OutlinedButton.icon(
                  icon: const Icon(
                    Icons.delete_outline,
                    size: 16,
                    color: Colors.red,
                  ),
                  label: const Text(
                    'Delete',
                    style: TextStyle(color: Colors.red),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Colors.red),
                  ),
                  onPressed: () => _handleDelete(context, notifier),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Future<void> _showRoleEditor(
    BuildContext context,
    WidgetRef ref,
    UserManagementNotifier notifier,
    bool isOwnAccount,
  ) async {
    if (allRoles.isEmpty) {
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(const SnackBar(content: Text('No roles available')));
      return;
    }

    final currentUser = ref.read(authProvider).valueOrNull;
    final adminRole = allRoles.firstWhere(
      (r) => r.name == 'admin' && r.isDefault,
      orElse: () => allRoles.first,
    );
    final isLastAdmin =
        user.roles.any((r) => r.id == adminRole.id) &&
        ref
                .read(usersProvider)
                .valueOrNull
                ?.where((u) => u.roles.any((r) => r.id == adminRole.id))
                .length ==
            1;

    final result = await showDialog<List<String>>(
      context: context,
      builder:
          (ctx) => _RoleEditorDialog(
            user: user,
            allRoles: allRoles,
            isOwnAccount: isOwnAccount,
            adminRoleId: adminRole.id,
            isLastAdmin: isLastAdmin,
            currentUserId: currentUser?.id,
          ),
    );
    if (result == null) return;

    try {
      await notifier.updateUserRoles(user.id, result);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Roles updated')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Failed to update roles: $e'),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
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
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(
          content: Text('Failed to reset password: $e'),
          backgroundColor: Colors.red,
        ),
      );
    }
  }

  Future<void> _handleDelete(
    BuildContext context,
    UserManagementNotifier notifier,
  ) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Delete member?'),
            content: Text(
              'Delete ${user.displayName.isNotEmpty ? user.displayName : user.phoneNumber}? '
              'This cannot be undone.',
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
    if (confirmed != true) return;
    try {
      await notifier.deleteUser(user.id);
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(
              '${user.displayName.isNotEmpty ? user.displayName : user.phoneNumber} deleted',
            ),
          ),
        );
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }

  void _showTempPasswordDialog(BuildContext context, String tempPassword) {
    showDialog<void>(
      context: context,
      builder:
          (ctx) => AlertDialog(
            title: const Text('Temporary password'),
            content: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Temporary password for '
                  '${user.displayName.isNotEmpty ? user.displayName : user.phoneNumber}:',
                ),
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
                  'Share with the member — they should change it on next login.',
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
}

class _RoleBadge extends StatelessWidget {
  final Role role;

  const _RoleBadge({required this.role});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.secondaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        role.name,
        style: TextStyle(
          fontSize: 11,
          fontWeight: FontWeight.w600,
          color: Theme.of(context).colorScheme.onSecondaryContainer,
        ),
      ),
    );
  }
}

// Dialog to assign/remove roles from a user
class _RoleEditorDialog extends StatefulWidget {
  final User user;
  final List<Role> allRoles;
  final bool isOwnAccount;
  final String adminRoleId;
  final bool isLastAdmin;
  final String? currentUserId;

  const _RoleEditorDialog({
    required this.user,
    required this.allRoles,
    required this.isOwnAccount,
    required this.adminRoleId,
    required this.isLastAdmin,
    required this.currentUserId,
  });

  @override
  State<_RoleEditorDialog> createState() => _RoleEditorDialogState();
}

class _RoleEditorDialogState extends State<_RoleEditorDialog> {
  late Set<String> _selected;

  @override
  void initState() {
    super.initState();
    _selected = widget.user.roles.map((r) => r.id).toSet();
  }

  bool _isLocked(Role role) {
    if (role.id != widget.adminRoleId) return false;
    if (widget.isLastAdmin && _selected.contains(role.id)) return true;
    if (widget.isOwnAccount && _selected.contains(role.id)) return true;
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(
        'Edit roles — ${widget.user.displayName.isNotEmpty ? widget.user.displayName : widget.user.phoneNumber}',
      ),
      content: SizedBox(
        width: 400,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children:
                widget.allRoles.map((role) {
                  final locked = _isLocked(role);
                  final checked = _selected.contains(role.id);
                  return CheckboxListTile(
                    value: checked,
                    onChanged:
                        locked
                            ? null
                            : (v) => setState(() {
                              if (v == true) {
                                _selected.add(role.id);
                              } else {
                                _selected.remove(role.id);
                              }
                            }),
                    title: Row(
                      children: [
                        Text(role.name),
                        if (locked) ...[
                          const SizedBox(width: 6),
                          Icon(
                            Icons.lock_outline,
                            size: 14,
                            color: Colors.grey[500],
                          ),
                        ],
                      ],
                    ),
                    subtitle:
                        role.permissions.isEmpty
                            ? null
                            : Text(
                              role.permissions
                                  .map((p) => _kPermissionLabels[p] ?? p)
                                  .join(', '),
                              style: const TextStyle(fontSize: 11),
                            ),
                  );
                }).toList(),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(_selected.toList()),
          child: const Text('Save'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Roles tab
// ---------------------------------------------------------------------------

class _RolesTab extends ConsumerWidget {
  final bool canManageRoles;

  const _RolesTab({required this.canManageRoles});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final rolesAsync = ref.watch(rolesProvider);

    return rolesAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(child: Text('Failed to load roles: $e')),
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
                    icon: const Icon(Icons.add, size: 18),
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
                    (context, index) => _RoleCard(
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
      builder: (_) => const _RoleFormDialog(),
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
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Role created')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }
}

class _RoleCard extends ConsumerWidget {
  final Role role;
  final bool canManageRoles;

  const _RoleCard({required this.role, required this.canManageRoles});

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
                        .map((p) => _PermissionChip(permission: p))
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
      builder: (_) => _RoleFormDialog(role: role),
    );
    if (result == null) return;

    try {
      await notifier.updateRole(
        role.id,
        List<String>.from(result['permissions'] as List),
      );
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Role updated')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
        );
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
                style: TextButton.styleFrom(foregroundColor: Colors.red),
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
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text('"${role.name}" deleted')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Failed: $e'), backgroundColor: Colors.red),
        );
      }
    }
  }
}

class _PermissionChip extends StatelessWidget {
  final String permission;

  const _PermissionChip({required this.permission});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: Theme.of(context).colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Text(
        _kPermissionLabels[permission] ?? permission,
        style: TextStyle(
          fontSize: 11,
          color: Theme.of(context).colorScheme.onPrimaryContainer,
        ),
      ),
    );
  }
}

// Dialog to create or edit a role (name + permission checkboxes)
class _RoleFormDialog extends StatefulWidget {
  final Role? role;

  const _RoleFormDialog({this.role});

  @override
  State<_RoleFormDialog> createState() => _RoleFormDialogState();
}

class _RoleFormDialogState extends State<_RoleFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late Set<String> _selectedPermissions;

  bool get _isEdit => widget.role != null;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.role?.name ?? '');
    _selectedPermissions = Set.from(widget.role?.permissions ?? []);
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEdit ? 'Edit role' : 'New role'),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (!_isEdit)
                  TextFormField(
                    controller: _name,
                    decoration: const InputDecoration(
                      labelText: 'Role name *',
                      border: OutlineInputBorder(),
                    ),
                    validator: v.roleName(),
                  ),
                if (!_isEdit) const SizedBox(height: 16),
                Text(
                  'Permissions',
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 4),
                ..._kPermissionLabels.entries.map((entry) {
                  return CheckboxListTile(
                    value: _selectedPermissions.contains(entry.key),
                    onChanged:
                        (v) => setState(() {
                          if (v == true) {
                            _selectedPermissions.add(entry.key);
                          } else {
                            _selectedPermissions.remove(entry.key);
                          }
                        }),
                    title: Text(entry.value),
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                  );
                }),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (!_formKey.currentState!.validate()) return;
            Navigator.of(context).pop({
              'name': _name.text.trim(),
              'permissions': _selectedPermissions.toList(),
            });
          },
          child: Text(_isEdit ? 'Save' : 'Create'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Add single member dialog
// ---------------------------------------------------------------------------

class _AddMemberDialog extends StatefulWidget {
  final List<Role> allRoles;

  const _AddMemberDialog({required this.allRoles});

  @override
  State<_AddMemberDialog> createState() => _AddMemberDialogState();
}

class _AddMemberDialogState extends State<_AddMemberDialog> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  String _phoneNumber = '';
  String? _selectedRoleId;

  @override
  void dispose() {
    _displayNameCtrl.dispose();
    _emailCtrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add member'),
      content: SizedBox(
        width: 440,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                IntlPhoneField(
                  initialCountryCode: 'US',
                  decoration: const InputDecoration(
                    labelText: 'Phone number *',
                    border: OutlineInputBorder(),
                  ),
                  onChanged: (phone) {
                    _phoneNumber = phone.completeNumber;
                  },
                  validator: (phone) {
                    if (phone == null || phone.number.isEmpty) {
                      return 'Required';
                    }
                    return null;
                  },
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _displayNameCtrl,
                  keyboardType: TextInputType.name,
                  decoration: const InputDecoration(
                    labelText: 'Display name (optional)',
                    border: OutlineInputBorder(),
                  ),
                  validator: v.maxLength(64),
                ),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _emailCtrl,
                  keyboardType: TextInputType.emailAddress,
                  decoration: const InputDecoration(
                    labelText: 'Email (optional)',
                    border: OutlineInputBorder(),
                  ),
                  validator: v.optionalEmail(),
                ),
                if (widget.allRoles.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _selectedRoleId,
                    decoration: const InputDecoration(
                      labelText: 'Role (optional)',
                      border: OutlineInputBorder(),
                    ),
                    items:
                        widget.allRoles
                            .map(
                              (r) => DropdownMenuItem(
                                value: r.id,
                                child: Text(r.name),
                              ),
                            )
                            .toList(),
                    onChanged: (val) => setState(() => _selectedRoleId = val),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (!_formKey.currentState!.validate()) return;
            Navigator.of(context).pop({
              'phone_number': _phoneNumber,
              'display_name': _displayNameCtrl.text.trim(),
              'email': _emailCtrl.text.trim(),
              if (_selectedRoleId != null) 'role_id': _selectedRoleId,
            });
          },
          child: const Text('Create'),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------------------
// Bulk add dialog — one phone number per line
// ---------------------------------------------------------------------------

class _BulkAddDialog extends StatefulWidget {
  final WidgetRef ref;

  const _BulkAddDialog({required this.ref});

  @override
  State<_BulkAddDialog> createState() => _BulkAddDialogState();
}

class _BulkAddDialogState extends State<_BulkAddDialog> {
  final _ctrl = TextEditingController();
  bool _loading = false;
  Map<String, dynamic>? _results;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  List<String> get _phones =>
      _ctrl.text
          .split('\n')
          .map((l) => l.trim())
          .where((l) => l.isNotEmpty)
          .toList();

  Future<void> _submit() async {
    final phones = _phones;
    if (phones.isEmpty) return;
    setState(() => _loading = true);
    try {
      final data = await widget.ref
          .read(userManagementProvider.notifier)
          .bulkCreateUsers(phones);
      setState(() {
        _results = data;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(ApiError.from(e).message),
            backgroundColor: Colors.red,
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Bulk add members'),
      content: SizedBox(
        width: 480,
        child: _results != null ? _buildResults(context) : _buildForm(context),
      ),
      actions:
          _results != null
              ? [
                TextButton(
                  onPressed: () => Navigator.of(context).pop(),
                  child: const Text('Done'),
                ),
              ]
              : [
                TextButton(
                  onPressed:
                      _loading ? null : () => Navigator.of(context).pop(),
                  child: const Text('Cancel'),
                ),
                FilledButton(
                  onPressed: (_loading || _phones.isEmpty) ? null : _submit,
                  child:
                      _loading
                          ? const SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          )
                          : Text(
                            'Add ${_phones.length} member${_phones.length == 1 ? '' : 's'}',
                          ),
                ),
              ],
    );
  }

  Widget _buildForm(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'One phone number per line. Members will be prompted to set a display name and password on first login.',
          style: TextStyle(fontSize: 13, color: Colors.grey),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _ctrl,
          maxLines: 8,
          onChanged: (_) => setState(() {}),
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: '+12125551234\n+13105559876\n…',
            alignLabelWithHint: true,
          ),
          style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
        ),
      ],
    );
  }

  Widget _buildResults(BuildContext context) {
    final results = (_results!['results'] as List).cast<Map<String, dynamic>>();
    final created = _results!['created'] as int;
    final failed = _results!['failed'] as int;
    final tempPassword = _results!['temporary_password'] as String;

    return SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$created created${failed > 0 ? ', $failed failed' : ''}',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color:
                  failed > 0
                      ? Theme.of(context).colorScheme.error
                      : Theme.of(context).colorScheme.primary,
            ),
          ),
          if (created > 0) ...[
            const SizedBox(height: 12),
            const Text('Temporary password (share with new members):'),
            const SizedBox(height: 6),
            Row(
              children: [
                Expanded(
                  child: SelectableText(
                    tempPassword,
                    style: const TextStyle(
                      fontFamily: 'monospace',
                      fontSize: 15,
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                ),
                IconButton(
                  icon: const Icon(Icons.copy, size: 18),
                  tooltip: 'Copy',
                  onPressed: () {
                    Clipboard.setData(ClipboardData(text: tempPassword));
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('Copied to clipboard')),
                    );
                  },
                ),
              ],
            ),
          ],
          if (failed > 0) ...[
            const SizedBox(height: 12),
            const Text(
              'Errors:',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            ...results
                .where((r) => r['success'] == false)
                .map(
                  (r) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text(
                      'Row ${r['row']}: ${r['phone_number']} — ${r['error']}',
                      style: TextStyle(
                        fontSize: 13,
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}
