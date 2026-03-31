import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/approval_credentials_dialog.dart';
import 'add_member_dialog.dart';
import 'role_form_dialog.dart';
import 'package:pda/config/constants.dart';

enum _SortField { name, phone, role }

class MembersTab extends ConsumerStatefulWidget {
  final bool canManageRoles;
  final bool canManageUsers;

  const MembersTab({
    super.key,
    required this.canManageRoles,
    required this.canManageUsers,
  });

  @override
  ConsumerState<MembersTab> createState() => _MembersTabState();
}

class _MembersTabState extends ConsumerState<MembersTab> {
  final _searchController = TextEditingController();
  String _query = '';
  _SortField _sort = _SortField.name;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<User> _filterAndSort(List<User> users) {
    var filtered = users;
    if (_query.isNotEmpty) {
      final q = _query.toLowerCase();
      filtered =
          users
              .where(
                (u) =>
                    u.displayName.toLowerCase().contains(q) ||
                    u.phoneNumber.contains(q) ||
                    u.email.toLowerCase().contains(q),
              )
              .toList();
    }
    filtered.sort((a, b) {
      return switch (_sort) {
        _SortField.name => a.displayName.toLowerCase().compareTo(
          b.displayName.toLowerCase(),
        ),
        _SortField.phone => a.phoneNumber.compareTo(b.phoneNumber),
        _SortField.role => (b.roles.length).compareTo(a.roles.length),
      };
    });
    return filtered;
  }

  @override
  Widget build(BuildContext context) {
    final usersAsync = ref.watch(usersProvider);
    final rolesAsync = ref.watch(rolesProvider);

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
          child: Column(
            children: [
              TextField(
                controller: _searchController,
                decoration: InputDecoration(
                  hintText: 'search members...',
                  prefixIcon: const Icon(Icons.search, size: 20),
                  isDense: true,
                  border: OutlineInputBorder(
                    borderRadius: BorderRadius.circular(8),
                  ),
                  contentPadding: const EdgeInsets.symmetric(
                    horizontal: 12,
                    vertical: 10,
                  ),
                  suffixIcon:
                      _query.isNotEmpty
                          ? IconButton(
                            icon: const Icon(Icons.close, size: 18),
                            tooltip: 'clear search',
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _query = '');
                            },
                          )
                          : null,
                ),
                onChanged: (v) => setState(() => _query = v),
              ),
              const SizedBox(height: 8),
              SingleChildScrollView(
                scrollDirection: Axis.horizontal,
                child: Row(
                  children: [
                    SegmentedButton<_SortField>(
                      segments: const [
                        ButtonSegment(
                          value: _SortField.name,
                          label: Text('name'),
                        ),
                        ButtonSegment(
                          value: _SortField.phone,
                          label: Text('phone'),
                        ),
                        ButtonSegment(
                          value: _SortField.role,
                          label: Text('role'),
                        ),
                      ],
                      selected: {_sort},
                      onSelectionChanged:
                          (s) => setState(() => _sort = s.first),
                      style: ButtonStyle(
                        visualDensity: VisualDensity.compact,
                        textStyle: WidgetStatePropertyAll(
                          Theme.of(context).textTheme.labelSmall,
                        ),
                      ),
                    ),
                    if (widget.canManageUsers) ...[
                      const SizedBox(width: 8),
                      OutlinedButton.icon(
                        onPressed: () => _showBulkAddDialog(context, ref),
                        icon: const Icon(Icons.group_add_outlined, size: 18),
                        label: const Text('Bulk add'),
                      ),
                      const SizedBox(width: 8),
                      FilledButton.icon(
                        onPressed: () => _showAddMemberDialog(context, ref),
                        icon: const Icon(
                          Icons.person_add_alt_1_outlined,
                          size: 18,
                        ),
                        label: const Text('Add member'),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
        Expanded(
          child: usersAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => Center(child: Text('Failed to load members: $e')),
            data: (users) {
              final filtered = _filterAndSort(users);
              if (filtered.isEmpty) {
                return Center(
                  child: Column(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: [
                      const Icon(
                        Icons.groups_outlined,
                        size: 64,
                        color: Colors.grey,
                      ),
                      const SizedBox(height: 16),
                      Text(
                        _query.isNotEmpty
                            ? 'no matches for "$_query"'
                            : 'no members found',
                        style: const TextStyle(
                          fontSize: 18,
                          color: Colors.grey,
                        ),
                      ),
                    ],
                  ),
                );
              }
              final allRoles = rolesAsync.valueOrNull ?? [];
              return ListView.separated(
                padding: const EdgeInsets.all(24),
                itemCount: filtered.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder:
                    (context, index) => MemberCard(
                      user: filtered[index],
                      allRoles: allRoles,
                      canManageRoles: widget.canManageRoles,
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
      builder: (_) => AddMemberDialog(allRoles: allRoles),
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
      showErrorSnackBar(context, ApiError.from(e).message);
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
          (_) => ApprovalCredentialsDialog(
            title: 'member created',
            body:
                '$displayName has been added. Share their temporary password:',
            tempPassword: tempPassword,
          ),
    );
  }

  Future<void> _showBulkAddDialog(BuildContext context, WidgetRef ref) async {
    await showDialog<void>(
      context: context,
      builder: (_) => BulkAddDialog(ref: ref),
    );
  }
}

class MemberCard extends ConsumerWidget {
  final User user;
  final List<Role> allRoles;
  final bool canManageRoles;

  const MemberCard({
    super.key,
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
      child: SelectionArea(
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
                        Row(
                          children: [
                            Flexible(
                              child: Text(
                                user.displayName.isNotEmpty
                                    ? user.displayName
                                    : '(no name)',
                                style: Theme.of(context).textTheme.titleMedium,
                              ),
                            ),
                            if (user.needsOnboarding) ...[
                              const SizedBox(width: 6),
                              Tooltip(
                                message: 'hasn\'t logged in yet',
                                child: Container(
                                  width: 8,
                                  height: 8,
                                  decoration: BoxDecoration(
                                    color:
                                        Theme.of(context).colorScheme.tertiary,
                                    shape: BoxShape.circle,
                                  ),
                                ),
                              ),
                            ],
                          ],
                        ),
                        const SizedBox(height: 2),
                        Text(
                          user.phoneNumber,
                          style: TextStyle(
                            color:
                                Theme.of(context).colorScheme.onSurfaceVariant,
                          ),
                        ),
                        if (user.email.isNotEmpty)
                          Text(
                            user.email,
                            style: TextStyle(
                              color:
                                  Theme.of(
                                    context,
                                  ).colorScheme.onSurfaceVariant,
                            ),
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
              if (user.roles.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: user.roles.map((r) => RoleBadge(role: r)).toList(),
                ),
              ],
              const SizedBox(height: 12),
              Wrap(
                spacing: 8,
                runSpacing: 8,
                children: [
                  if (canManageRoles)
                    OutlinedButton.icon(
                      icon: const Icon(Icons.verified_user_outlined, size: 16),
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
                    icon: const Icon(Icons.key_outlined, size: 16),
                    label: const Text('Reset password'),
                    onPressed: () => _handleResetPassword(context, notifier),
                  ),
                  OutlinedButton.icon(
                    icon: Icon(
                      Icons.delete_outline,
                      size: 16,
                      color: Theme.of(context).colorScheme.error,
                    ),
                    label: Text(
                      'Delete',
                      style: TextStyle(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                    style: OutlinedButton.styleFrom(
                      side: BorderSide(
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                    onPressed: () => _handleDelete(context, notifier),
                  ),
                ],
              ),
            ],
          ),
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
      showSnackBar(context, 'No roles available');
      return;
    }

    final currentUser = ref.read(authProvider).valueOrNull;
    final adminRole = allRoles.firstWhere(
      (r) => r.name == RoleName.admin && r.isDefault,
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
          (ctx) => RoleEditorDialog(
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
        showSnackBar(context, 'Roles updated');
      }
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, 'Failed to update roles: $e');
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
      showErrorSnackBar(context, 'Failed to reset password: $e');
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
      await notifier.deleteUser(user.id);
      if (context.mounted) {
        showSnackBar(
          context,
          '${user.displayName.isNotEmpty ? user.displayName : user.phoneNumber} deleted',
        );
      }
    } catch (e) {
      if (context.mounted) {
        showErrorSnackBar(context, 'Failed: $e');
      }
    }
  }

  void _showTempPasswordDialog(BuildContext context, String tempPassword) {
    final name =
        user.displayName.isNotEmpty ? user.displayName : user.phoneNumber;
    showDialog<void>(
      context: context,
      builder:
          (_) => ApprovalCredentialsDialog(
            title: 'Temporary password',
            body: 'Temporary password for $name:',
            tempPassword: tempPassword,
          ),
    );
  }
}

class RoleBadge extends StatelessWidget {
  final Role role;

  const RoleBadge({super.key, required this.role});

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
