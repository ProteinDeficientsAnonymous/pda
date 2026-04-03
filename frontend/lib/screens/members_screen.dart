import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/config/constants.dart';
import 'members/members_tab.dart';
import 'members/roles_tab.dart';

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
    final currentUser = ref.watch(authProvider).value;
    final canManageRoles =
        currentUser?.hasPermission(Permission.manageRoles) ?? false;
    final canManageUsers =
        currentUser?.hasPermission(Permission.manageUsers) ?? false;

    return AppScaffold(
      child: Column(
        children: [
          TabBar(
            controller: _tabController,
            tabs: const [
              Tab(text: 'Members'),
              Tab(text: 'Roles'),
            ],
          ),
          Expanded(
            child: TabBarView(
              controller: _tabController,
              children: [
                MembersTab(
                  canManageRoles: canManageRoles,
                  canManageUsers: canManageUsers,
                ),
                RolesTab(canManageRoles: canManageRoles),
              ],
            ),
          ),
        ],
      ),
    );
  }
}
