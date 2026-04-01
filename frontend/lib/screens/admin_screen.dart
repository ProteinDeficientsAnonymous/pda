import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/config/constants.dart';

class AdminScreen extends ConsumerWidget {
  const AdminScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;
    final cards = _buildCards(context, user);

    return AppScaffold(
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('admin', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 20),
            LayoutBuilder(
              builder: (context, constraints) {
                if (constraints.maxWidth < 600) {
                  return Column(children: cards);
                }
                return Wrap(spacing: 16, runSpacing: 16, children: cards);
              },
            ),
          ],
        ),
      ),
    );
  }
}

List<Widget> _buildCards(BuildContext context, dynamic user) {
  return [
    if (user?.hasPermission(Permission.manageEvents) ?? false)
      _AdminCard(
        icon: Icons.event_available_outlined,
        title: 'manage events',
        subtitle: 'create, edit, and manage events',
        onTap: () => context.go('/events/manage'),
      ),
    if (user?.hasPermission(Permission.manageUsers) ?? false)
      _AdminCard(
        icon: Icons.groups_outlined,
        title: 'members',
        subtitle: 'view and manage member accounts',
        onTap: () => context.go('/members'),
      ),
    if (user?.hasPermission(Permission.approveJoinRequests) ?? false)
      _AdminCard(
        icon: Icons.person_search_outlined,
        title: 'join requests',
        subtitle: 'review pending membership requests',
        onTap: () => context.go('/join-requests'),
      ),
    if (user?.hasPermission(Permission.editJoinQuestions) ?? false)
      _AdminCard(
        icon: Icons.dynamic_form_outlined,
        title: 'join form',
        subtitle: 'configure join request form questions',
        onTap: () => context.go('/admin/join-form'),
      ),
    if (user?.hasPermission(Permission.manageSurveys) ?? false)
      _AdminCard(
        icon: Icons.poll_outlined,
        title: 'surveys',
        subtitle: 'create and manage feedback surveys',
        onTap: () => context.go('/admin/surveys'),
      ),
    if (user?.hasPermission(Permission.manageDocs) ?? false)
      _AdminCard(
        icon: Icons.library_books_outlined,
        title: 'documents',
        subtitle: 'create and manage shared docs',
        onTap: () => context.go('/docs'),
      ),
    if (user?.hasPermission(Permission.manageWhatsapp) ?? false)
      _AdminCard(
        icon: Icons.chat_outlined,
        title: 'whatsapp bot',
        subtitle: 'configure bot connection and group',
        onTap: () => context.go('/admin/whatsapp'),
      ),
  ];
}

class _AdminCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final VoidCallback onTap;

  const _AdminCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return ConstrainedBox(
      constraints: const BoxConstraints(maxWidth: 400),
      child: Card(
        child: ListTile(
          leading: Icon(icon, color: Theme.of(context).colorScheme.primary),
          title: Text(title),
          subtitle: Text(subtitle),
          trailing: const Icon(Icons.chevron_right),
          onTap: onTap,
        ),
      ),
    );
  }
}
