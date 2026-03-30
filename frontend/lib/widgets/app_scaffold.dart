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
    final canPop = Navigator.of(context).canPop();

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: !isWide,
        leading:
            canPop
                ? BackButton(onPressed: () => Navigator.of(context).pop())
                : null,
        title:
            isWide
                ? const Align(
                  alignment: Alignment.centerLeft,
                  child: _NavButton(label: 'PDA', route: '/'),
                )
                : null,
        actions: isWide ? _buildWideNavItems(context, ref, user) : null,
      ),
      drawer: isWide ? null : _NavDrawer(user: user),
      body: child,
    );
  }
}

List<Widget> _buildWideNavItems(
  BuildContext context,
  WidgetRef ref,
  User? user,
) {
  if (user == null) {
    return [
      const _NavButton(label: 'calendar', route: '/calendar'),
      const _NavButton(label: 'faq', route: '/faq'),
      const _NavButton(label: 'donate', route: '/donate'),
      const _NavButton(label: 'log in', route: '/login'),
    ];
  }

  return [
    const _NavButton(label: 'calendar', route: '/calendar'),
    const _NavButton(label: 'my events', route: '/events/mine'),
    const _NavButton(label: 'guidelines', route: '/guidelines'),
    const _NavButton(label: 'faq', route: '/faq'),
    const _NavButton(label: 'volunteer', route: '/volunteer'),
    const _NavButton(label: 'donate', route: '/donate'),
    if (user.hasAnyAdminPermission)
      const _NavButton(label: 'admin', route: '/admin'),
    const _NavButton(label: 'settings', route: '/settings'),
    TextButton(
      onPressed: () async {
        await ref.read(authProvider.notifier).logout();
        if (context.mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('you\'re logged out')));
        }
      },
      child: const Text('log out'),
    ),
  ];
}

class _NavButton extends StatelessWidget {
  final String label;
  final String route;

  const _NavButton({required this.label, required this.route});

  @override
  Widget build(BuildContext context) {
    final currentPath = GoRouterState.of(context).uri.path;
    final isActive =
        route == '/' ? currentPath == '/' : currentPath.startsWith(route);
    final isPda = route == '/';

    return TextButton(
      onPressed: () => context.go(route),
      style:
          isPda
              ? TextButton.styleFrom(
                foregroundColor: Theme.of(context).colorScheme.primary,
                textStyle: const TextStyle(
                  fontWeight: FontWeight.bold,
                  fontSize: 16,
                  letterSpacing: 1.5,
                ),
              )
              : isActive
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

    final mainItems = <_DrawerItem>[
      const _DrawerItem(icon: Icons.eco_outlined, label: 'PDA', route: '/'),
      const _DrawerItem(
        icon: Icons.calendar_month_outlined,
        label: 'calendar',
        route: '/calendar',
      ),
      if (user != null)
        const _DrawerItem(
          icon: Icons.event_outlined,
          label: 'my events',
          route: '/events/mine',
        ),
    ];

    return Drawer(
      semanticLabel: 'Navigation menu',
      child: SafeArea(
        child: Column(
          children: [
            // Shared header
            _DrawerHeader(theme: theme),
            const Divider(),
            Expanded(
              child: ListView(
                padding: EdgeInsets.zero,
                children:
                    mainItems
                        .map(
                          (item) => _DrawerNavTile(
                            item: item,
                            currentPath: currentPath,
                            theme: theme,
                          ),
                        )
                        .toList(),
              ),
            ),
            // Shared bottom section
            const Divider(),
            _DrawerNavTile(
              item: const _DrawerItem(
                icon: Icons.spa_outlined,
                label: 'guidelines',
                route: '/guidelines',
              ),
              currentPath: currentPath,
              theme: theme,
            ),
            _DrawerNavTile(
              item: const _DrawerItem(
                icon: Icons.chat_bubble_outline,
                label: 'faq',
                route: '/faq',
              ),
              currentPath: currentPath,
              theme: theme,
            ),
            if (user != null) ...[
              _DrawerNavTile(
                item: const _DrawerItem(
                  icon: Icons.favorite_outline,
                  label: 'volunteer',
                  route: '/volunteer',
                ),
                currentPath: currentPath,
                theme: theme,
              ),
              _DrawerNavTile(
                item: const _DrawerItem(
                  icon: Icons.local_florist_outlined,
                  label: 'donate',
                  route: '/donate',
                ),
                currentPath: currentPath,
                theme: theme,
              ),
              if (user!.hasAnyAdminPermission)
                _DrawerNavTile(
                  item: const _DrawerItem(
                    icon: Icons.dashboard_outlined,
                    label: 'admin',
                    route: '/admin',
                  ),
                  currentPath: currentPath,
                  theme: theme,
                ),
              _DrawerNavTile(
                item: const _DrawerItem(
                  icon: Icons.tune_outlined,
                  label: 'settings',
                  route: '/settings',
                ),
                currentPath: currentPath,
                theme: theme,
              ),
              ListTile(
                leading: Icon(
                  Icons.logout_outlined,
                  color: theme.colorScheme.error,
                ),
                title: Text(
                  'log out',
                  style: TextStyle(color: theme.colorScheme.error),
                ),
                onTap: () async {
                  Navigator.of(context).pop();
                  await ref.read(authProvider.notifier).logout();
                  if (context.mounted) {
                    ScaffoldMessenger.of(context).showSnackBar(
                      const SnackBar(content: Text('you\'re logged out')),
                    );
                  }
                },
              ),
            ] else
              ListTile(
                leading: const Icon(Icons.login_outlined),
                title: const Text('log in'),
                onTap: () {
                  Navigator.of(context).pop();
                  context.go('/login');
                },
              ),
          ],
        ),
      ),
    );
  }
}

class _DrawerHeader extends StatelessWidget {
  const _DrawerHeader({required this.theme});

  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return Padding(
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
    );
  }
}

class _DrawerNavTile extends StatelessWidget {
  const _DrawerNavTile({
    required this.item,
    required this.currentPath,
    required this.theme,
  });

  final _DrawerItem item;
  final String currentPath;
  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    final isSelected =
        item.route == '/'
            ? currentPath == '/'
            : currentPath.startsWith(item.route);
    return ListTile(
      leading: Icon(item.icon),
      title: Text(item.label),
      selected: isSelected,
      selectedTileColor: theme.colorScheme.primaryContainer,
      onTap: () {
        Navigator.of(context).pop();
        context.go(item.route);
      },
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
