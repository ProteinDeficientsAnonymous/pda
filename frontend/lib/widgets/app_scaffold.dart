import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';

class AppScaffold extends ConsumerWidget {
  final Widget child;
  final String? title;

  const AppScaffold({super.key, required this.child, this.title});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final user = authState.valueOrNull;

    return Scaffold(
      appBar: AppBar(
        title: Text(title ?? 'Protein Deficients Anonymous'),
        actions: [
          if (user == null) ...[
            TextButton(
              onPressed: () => context.go('/login'),
              child: const Text('Member login'),
            ),
          ] else ...[
            TextButton(
              onPressed: () => context.go('/calendar'),
              child: const Text('Calendar'),
            ),
            TextButton(
              onPressed: () => context.go('/members'),
              child: const Text('Members'),
            ),
            TextButton(
              onPressed: () => context.go('/join-requests'),
              child: const Text('Join requests'),
            ),
            TextButton(
              onPressed: () => context.go('/events/manage'),
              child: const Text('Manage events'),
            ),
            TextButton(
              onPressed: () => ref.read(authProvider.notifier).logout(),
              child: const Text('Logout'),
            ),
          ],
        ],
      ),
      body: child,
    );
  }
}
