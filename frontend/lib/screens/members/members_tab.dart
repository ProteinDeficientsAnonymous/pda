import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/approval_credentials_dialog.dart';
import 'add_member_dialog.dart';
import 'member_card.dart';

export 'member_card.dart' show MemberCard, RoleBadge;

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
    var filtered = [...users];
    if (_query.isNotEmpty) {
      final q = _query.toLowerCase();
      filtered = users
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
                  suffixIcon: _query.isNotEmpty
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
              Wrap(
                spacing: 8,
                runSpacing: 8,
                alignment: WrapAlignment.center,
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
                    onSelectionChanged: (s) => setState(() => _sort = s.first),
                    showSelectedIcon: false,
                    style: ButtonStyle(
                      visualDensity: VisualDensity.compact,
                      textStyle: WidgetStatePropertyAll(
                        Theme.of(context).textTheme.labelSmall,
                      ),
                    ),
                  ),
                  if (widget.canManageUsers) ...[
                    OutlinedButton.icon(
                      onPressed: () => _showBulkAddDialog(context, ref),
                      icon: const Icon(Icons.group_add_outlined, size: 18),
                      label: const Text('bulk add'),
                    ),
                    FilledButton.icon(
                      onPressed: () => _showAddMemberDialog(context, ref),
                      icon: const Icon(
                        Icons.person_add_alt_1_outlined,
                        size: 18,
                      ),
                      label: const Text('add member'),
                    ),
                  ],
                ],
              ),
            ],
          ),
        ),
        Expanded(
          child: usersAsync.when(
            loading: () => const Center(child: CircularProgressIndicator()),
            error: (e, _) => const Center(
              child: Text('couldn\'t load members — try refreshing'),
            ),
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
              final allRoles = rolesAsync.value ?? [];
              return ListView.separated(
                padding: const EdgeInsets.all(24),
                itemCount: filtered.length,
                separatorBuilder: (_, __) => const SizedBox(height: 12),
                itemBuilder: (context, index) => MemberCard(
                  user: filtered[index],
                  allRoles: allRoles,
                  canManageRoles: widget.canManageRoles,
                  canManageUsers: widget.canManageUsers,
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
    final allRoles = rolesAsync.value ?? [];
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
            roleId: result['role_id'] as String?,
          );
      if (!context.mounted) return;
      _showCreatedPasswordDialog(
        context,
        displayName:
            data['display_name'] as String? ?? data['phone_number'] as String,
        magicLinkToken: data['magic_link_token'] as String,
      );
    } catch (e) {
      if (!context.mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    }
  }

  void _showCreatedPasswordDialog(
    BuildContext context, {
    required String displayName,
    required String magicLinkToken,
  }) {
    showDialog<void>(
      context: context,
      builder: (_) => ApprovalCredentialsDialog(
        title: 'member created',
        body: '$displayName has been added — share their login link:',
        magicLinkToken: magicLinkToken,
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
