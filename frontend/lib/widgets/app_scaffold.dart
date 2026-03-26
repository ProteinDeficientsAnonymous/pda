import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';

class AppScaffold extends ConsumerWidget {
  final Widget child;
  final String? title;

  const AppScaffold({super.key, required this.child, this.title});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState.valueOrNull;
    final isWide = MediaQuery.sizeOf(context).width >= 720;

    final navItems = _buildNavItems(context, ref, user);

    return Scaffold(
      appBar: AppBar(
        title: Text(title ?? 'Protein Deficients Anonymous'),
        actions: isWide ? navItems : null,
      ),
      drawer: isWide ? null : _NavDrawer(items: navItems),
      body: child,
    );
  }

  List<Widget> _buildNavItems(BuildContext context, WidgetRef ref, User? user) {
    if (user == null) {
      return [
        TextButton(
          onPressed: () => context.go('/login'),
          child: const Text('Member login'),
        ),
      ];
    }

    return [
      TextButton(
        onPressed: () => context.go('/calendar'),
        child: const Text('Calendar'),
      ),
      TextButton(
        onPressed: () => context.go('/events/mine'),
        child: const Text('My events'),
      ),
      if (user.hasPermission('manage_events'))
        TextButton(
          onPressed: () => context.go('/events/manage'),
          child: const Text('Manage events'),
        ),
      if (user.hasPermission('manage_users'))
        TextButton(
          onPressed: () => context.go('/members'),
          child: const Text('Members'),
        ),
      if (user.hasPermission('approve_join_requests'))
        TextButton(
          onPressed: () => context.go('/join-requests'),
          child: const Text('Join requests'),
        ),
      TextButton(
        onPressed: () => ref.read(authProvider.notifier).logout(),
        child: const Text('Logout'),
      ),
    ];
  }
}

class _NavDrawer extends StatelessWidget {
  final List<Widget> items;

  const _NavDrawer({required this.items});

  @override
  Widget build(BuildContext context) {
    return Drawer(
      child: ListView(
        padding: EdgeInsets.zero,
        children: [
          DrawerHeader(
            decoration: BoxDecoration(
              color: Theme.of(context).colorScheme.primaryContainer,
            ),
            child: Text(
              'Protein Deficients Anonymous',
              style: Theme.of(context).textTheme.titleMedium?.copyWith(
                color: Theme.of(context).colorScheme.onPrimaryContainer,
              ),
            ),
          ),
          ...items.map((item) => _DrawerNavItem(child: item)),
        ],
      ),
    );
  }
}

/// Wraps a TextButton nav item as a full-width drawer list tile.
class _DrawerNavItem extends StatelessWidget {
  final Widget child;

  const _DrawerNavItem({required this.child});

  @override
  Widget build(BuildContext context) {
    // Extract the TextButton's label and onPressed via a Builder trick —
    // instead, we just wrap in a ListTile-style container and let the
    // TextButton fill it naturally.
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 2),
      child: SizedBox(
        width: double.infinity,
        child: Align(alignment: Alignment.centerLeft, child: child),
      ),
    );
  }
}
