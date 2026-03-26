import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/onboarding_modal.dart';

class AppScaffold extends ConsumerStatefulWidget {
  final Widget child;

  const AppScaffold({super.key, required this.child});

  @override
  ConsumerState<AppScaffold> createState() => _AppScaffoldState();
}

class _AppScaffoldState extends ConsumerState<AppScaffold> {
  bool _onboardingShown = false;

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).valueOrNull;
    final isWide = MediaQuery.sizeOf(context).width >= 720;
    final canPop = Navigator.of(context).canPop();

    if (user != null && user.needsOnboarding && !_onboardingShown) {
      _onboardingShown = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        showDialog<void>(
          context: context,
          barrierDismissible: false,
          builder: (_) => const OnboardingModal(),
        ).then((_) {
          if (!mounted) return;
          final currentUser = ref.read(authProvider).valueOrNull;
          if (currentUser != null && currentUser.needsOnboarding) {
            setState(() => _onboardingShown = false);
          }
        });
      });
    }

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
        actions: isWide ? _wideNavItems(context, user) : null,
      ),
      drawer: isWide ? null : _NavDrawer(user: user),
      body: widget.child,
    );
  }

  List<Widget> _wideNavItems(BuildContext context, User? user) {
    if (user == null) {
      return [const _NavButton(label: 'Member login', route: '/login')];
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
      const _NavButton(label: 'Guidelines', route: '/guidelines'),
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
      const _DrawerItem(icon: Icons.home_outlined, label: 'PDA', route: '/'),
      const _DrawerItem(
        icon: Icons.calendar_month,
        label: 'Calendar',
        route: '/calendar',
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
                            selected:
                                item.route == '/'
                                    ? currentPath == '/'
                                    : currentPath.startsWith(item.route),
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
              leading: const Icon(Icons.menu_book_outlined),
              title: const Text('Guidelines'),
              selected: currentPath.startsWith('/guidelines'),
              selectedTileColor: theme.colorScheme.primaryContainer,
              onTap: () {
                Navigator.of(context).pop();
                context.go('/guidelines');
              },
            ),
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
