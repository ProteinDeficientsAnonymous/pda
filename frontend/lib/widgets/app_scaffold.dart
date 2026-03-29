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
      const _NavButton(label: 'Donate', route: '/donate'),
      const _NavButton(label: 'Member login', route: '/login'),
    ];
  }

  return [
    const _NavButton(label: 'Calendar', route: '/calendar'),
    const _NavButton(label: 'My events', route: '/events/mine'),
    if (user.hasPermission('manage_events'))
      const _NavButton(label: 'Manage events', route: '/events/manage'),
    if (user.hasPermission('manage_users'))
      const _NavButton(label: 'Members', route: '/members'),
    if (user.hasPermission('approve_join_requests'))
      const _NavButton(label: 'Join requests', route: '/join-requests'),
    if (user.hasPermission('manage_whatsapp'))
      const _NavButton(label: 'WhatsApp', route: '/admin/whatsapp'),
    const _NavButton(label: 'Donate', route: '/donate'),
    const _NavButton(label: 'Volunteer', route: '/volunteer'),
    const _NavButton(label: 'Guidelines', route: '/guidelines'),
    const _NavButton(label: 'FAQ', route: '/faq'),
    const _NavButton(label: 'Settings', route: '/settings'),
    TextButton(
      onPressed: () async {
        await ref.read(authProvider.notifier).logout();
        if (context.mounted) {
          ScaffoldMessenger.of(
            context,
          ).showSnackBar(const SnackBar(content: Text('Logged out')));
        }
      },
      child: const Text('Logout'),
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

    final mainItems =
        user == null
            ? <_DrawerItem>[]
            : <_DrawerItem>[
              const _DrawerItem(
                icon: Icons.eco_outlined,
                label: 'PDA',
                route: '/',
              ),
              const _DrawerItem(
                icon: Icons.calendar_month_outlined,
                label: 'Calendar',
                route: '/calendar',
              ),
              const _DrawerItem(
                icon: Icons.bookmark_outline,
                label: 'My events',
                route: '/events/mine',
              ),
              if (user!.hasPermission('manage_events'))
                const _DrawerItem(
                  icon: Icons.event_available_outlined,
                  label: 'Manage events',
                  route: '/events/manage',
                ),
              if (user!.hasPermission('manage_users'))
                const _DrawerItem(
                  icon: Icons.groups_outlined,
                  label: 'Members',
                  route: '/members',
                ),
              if (user!.hasPermission('approve_join_requests'))
                const _DrawerItem(
                  icon: Icons.person_search_outlined,
                  label: 'Join requests',
                  route: '/join-requests',
                ),
              if (user!.hasPermission('manage_whatsapp'))
                const _DrawerItem(
                  icon: Icons.chat_outlined,
                  label: 'WhatsApp',
                  route: '/admin/whatsapp',
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
            // Main nav (empty for logged-out → Spacer fills the gap)
            mainItems.isEmpty
                ? const Spacer()
                : Expanded(
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
                icon: Icons.volunteer_activism_outlined,
                label: 'Donate',
                route: '/donate',
              ),
              currentPath: currentPath,
              theme: theme,
            ),
            if (user != null) ...[
              _DrawerNavTile(
                item: const _DrawerItem(
                  icon: Icons.handshake_outlined,
                  label: 'Volunteer',
                  route: '/volunteer',
                ),
                currentPath: currentPath,
                theme: theme,
              ),
              _DrawerNavTile(
                item: const _DrawerItem(
                  icon: Icons.auto_stories_outlined,
                  label: 'Guidelines',
                  route: '/guidelines',
                ),
                currentPath: currentPath,
                theme: theme,
              ),
              _DrawerNavTile(
                item: const _DrawerItem(
                  icon: Icons.quiz_outlined,
                  label: 'FAQ',
                  route: '/faq',
                ),
                currentPath: currentPath,
                theme: theme,
              ),
              _DrawerNavTile(
                item: const _DrawerItem(
                  icon: Icons.tune_outlined,
                  label: 'Settings',
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
                  'Logout',
                  style: TextStyle(color: theme.colorScheme.error),
                ),
                onTap: () async {
                  Navigator.of(context).pop();
                  await ref.read(authProvider.notifier).logout();
                  if (context.mounted) {
                    ScaffoldMessenger.of(
                      context,
                    ).showSnackBar(const SnackBar(content: Text('Logged out')));
                  }
                },
              ),
            ] else
              ListTile(
                leading: const Icon(Icons.login_outlined),
                title: const Text('Member login'),
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
