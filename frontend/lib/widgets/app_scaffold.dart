import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';

class AppScaffold extends ConsumerWidget {
  final Widget child;

  const AppScaffold({super.key, required this.child});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    final isWide = MediaQuery.sizeOf(context).width >= 720;

    return Scaffold(
      appBar: AppBar(
        title: null,
        actions: isWide ? _wideNavItems(context, ref, user) : null,
      ),
      drawer: isWide ? null : _NavDrawer(user: user),
      body: child,
    );
  }

  List<Widget> _wideNavItems(BuildContext context, WidgetRef ref, User? user) {
    if (user == null) {
      return [const _NavButton(label: 'Member login', route: '/login')];
    }

    return [
      const _NavButton(label: 'Calendar', route: '/calendar'),
      const _NavButton(label: 'Guidelines', route: '/guidelines'),
      const _NavButton(label: 'My events', route: '/events/mine'),
      if (user.hasPermission('manage_events'))
        const _NavButton(label: 'Manage events', route: '/events/manage'),
      if (user.hasPermission('manage_users'))
        const _NavButton(label: 'Members', route: '/members'),
      if (user.hasPermission('approve_join_requests'))
        const _NavButton(label: 'Join requests', route: '/join-requests'),
      const _NavButton(label: 'Settings', route: '/settings'),
      TextButton(
        onPressed: () => ref.read(authProvider.notifier).logout(),
        child: const Text('Logout'),
      ),
    ];
  }
}

class _NavButton extends StatelessWidget {
  final String label;
  final String route;

  const _NavButton({required this.label, required this.route});

  @override
  Widget build(BuildContext context) {
    final currentPath = GoRouterState.of(context).uri.path;
    final isActive = currentPath.startsWith(route);

    return TextButton(
      onPressed: () => context.go(route),
      style:
          isActive
              ? TextButton.styleFrom(
                foregroundColor: Theme.of(context).colorScheme.primary,
                textStyle: const TextStyle(fontWeight: FontWeight.bold),
              )
              : null,
      child: Text(label),
    );
  }
}

class _NavDrawer extends ConsumerWidget {
  final User? user;

  const _NavDrawer({required this.user});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final currentPath = GoRouterState.of(context).uri.path;

    if (user == null) {
      return Drawer(
        child: SafeArea(
          child: ListTile(
            leading: const Icon(Icons.login),
            title: const Text('Member login'),
            onTap: () {
              Navigator.of(context).pop();
              context.go('/login');
            },
          ),
        ),
      );
    }

    final mainItems = <_DrawerItem>[
      const _DrawerItem(
        icon: Icons.calendar_month,
        label: 'Calendar',
        route: '/calendar',
      ),
      const _DrawerItem(
        icon: Icons.menu_book_outlined,
        label: 'Guidelines',
        route: '/guidelines',
      ),
      const _DrawerItem(
        icon: Icons.event_note,
        label: 'My events',
        route: '/events/mine',
      ),
      if (user!.hasPermission('manage_events'))
        const _DrawerItem(
          icon: Icons.edit_calendar,
          label: 'Manage events',
          route: '/events/manage',
        ),
      if (user!.hasPermission('manage_users'))
        const _DrawerItem(
          icon: Icons.group,
          label: 'Members',
          route: '/members',
        ),
      if (user!.hasPermission('approve_join_requests'))
        const _DrawerItem(
          icon: Icons.how_to_reg,
          label: 'Join requests',
          route: '/join-requests',
        ),
    ];

    return Drawer(
      child: SafeArea(
        child: Column(
          children: [
            // Compact header
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 16, 16, 8),
              child: Align(
                alignment: Alignment.centerLeft,
                child: Text(
                  'PDA',
                  style: theme.textTheme.titleLarge?.copyWith(
                    fontWeight: FontWeight.bold,
                    color: theme.colorScheme.primary,
                  ),
                ),
              ),
            ),
            const Divider(),
            // Main nav
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children:
                    mainItems
                        .map(
                          (item) => ListTile(
                            leading: Icon(item.icon),
                            title: Text(item.label),
                            selected: currentPath.startsWith(item.route),
                            selectedTileColor:
                                theme.colorScheme.primaryContainer,
                            onTap: () {
                              Navigator.of(context).pop();
                              context.go(item.route);
                            },
                          ),
                        )
                        .toList(),
              ),
            ),
            // Bottom actions
            const Divider(),
            ListTile(
              leading: const Icon(Icons.settings_outlined),
              title: const Text('Settings'),
              selected: currentPath.startsWith('/settings'),
              selectedTileColor: theme.colorScheme.primaryContainer,
              onTap: () {
                Navigator.of(context).pop();
                context.go('/settings');
              },
            ),
            ListTile(
              leading: Icon(Icons.logout, color: theme.colorScheme.error),
              title: Text(
                'Logout',
                style: TextStyle(color: theme.colorScheme.error),
              ),
              onTap: () {
                Navigator.of(context).pop();
                ref.read(authProvider.notifier).logout();
              },
            ),
          ],
        ),
      ),
    );
  }
}

class _DrawerItem {
  final IconData icon;
  final String label;
  final String route;

  const _DrawerItem({
    required this.icon,
    required this.label,
    required this.route,
  });
}
