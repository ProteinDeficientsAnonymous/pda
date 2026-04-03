import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/config/api_config.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/feedback_button.dart';
import 'package:pda/widgets/notification_bell.dart';
import 'package:pda/widgets/profile_avatar.dart';

class AppScaffold extends ConsumerWidget {
  final Widget child;
  final List<Widget>? actions;

  /// When set, body content is centered with this max width.
  final double? maxWidth;

  const AppScaffold({
    super.key,
    required this.child,
    this.actions,
    this.maxWidth,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).value;

    final body = maxWidth != null
        ? _CenteredBody(maxWidth: maxWidth!, child: child)
        : child;

    return Scaffold(
      appBar: AppBar(
        automaticallyImplyLeading: false,
        title: _LogoButton(onTap: () => _showPdaMenu(context, user)),
        actions: [if (user != null) const NotificationBell(), ...?actions],
      ),
      body: enableFeedback && user != null
          ? Stack(
              children: [
                body,
                FeedbackButton(
                  currentRoute: GoRouterState.of(context).uri.toString(),
                ),
              ],
            )
          : body,
      bottomNavigationBar: _BottomNav(user: user),
    );
  }
}

// ---------------------------------------------------------------------------
// Centered body wrapper
// ---------------------------------------------------------------------------

class _CenteredBody extends StatelessWidget {
  final double maxWidth;
  final Widget child;

  const _CenteredBody({required this.maxWidth, required this.child});

  @override
  Widget build(BuildContext context) {
    return Center(
      child: ConstrainedBox(
        constraints: BoxConstraints(maxWidth: maxWidth),
        child: child,
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Pea pod logo button (top left)
// ---------------------------------------------------------------------------

class _LogoButton extends StatelessWidget {
  final VoidCallback onTap;

  const _LogoButton({required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(8),
        child: Semantics(
          button: true,
          label: 'PDA menu',
          child: SizedBox(
            height: 48,
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4),
              child: Image.asset(
                'assets/logo.png',
                height: 32,
                errorBuilder: (_, __, ___) => const SizedBox(height: 32),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// PDA menu (org-specific pages)
// ---------------------------------------------------------------------------

void _showPdaMenu(BuildContext context, User? user) {
  showModalBottomSheet<void>(
    context: context,
    builder: (context) {
      return SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 8),
            if (user != null)
              ListTile(
                leading: const Icon(Icons.spa_outlined),
                title: const Text('guidelines'),
                onTap: () {
                  Navigator.pop(context);
                  context.go('/guidelines');
                },
              ),
            ListTile(
              leading: const Icon(Icons.chat_bubble_outline),
              title: const Text('faq'),
              onTap: () {
                Navigator.pop(context);
                context.go('/faq');
              },
            ),
            if (user != null)
              ListTile(
                leading: const Icon(Icons.library_books_outlined),
                title: const Text('docs'),
                onTap: () {
                  Navigator.pop(context);
                  context.go('/docs');
                },
              ),
            if (user != null)
              ListTile(
                leading: const Icon(Icons.favorite_outline),
                title: const Text('volunteer'),
                onTap: () {
                  Navigator.pop(context);
                  context.go('/volunteer');
                },
              ),
            ListTile(
              leading: const Icon(Icons.local_florist_outlined),
              title: const Text('donate'),
              onTap: () {
                Navigator.pop(context);
                context.go('/donate');
              },
            ),
            const SizedBox(height: 8),
          ],
        ),
      );
    },
  );
}

// ---------------------------------------------------------------------------
// Bottom navigation bar
// ---------------------------------------------------------------------------

class _BottomNav extends StatelessWidget {
  final User? user;

  const _BottomNav({required this.user});

  @override
  Widget build(BuildContext context) {
    final currentPath = GoRouterState.of(context).uri.path;

    final isCalendar =
        currentPath.startsWith('/calendar') ||
        currentPath.startsWith('/events');
    final isProfile =
        currentPath == '/profile' ||
        currentPath == '/settings' ||
        currentPath == '/admin' ||
        currentPath.startsWith('/admin/') ||
        currentPath == '/join-requests' ||
        currentPath == '/members' ||
        currentPath.startsWith('/surveys') ||
        currentPath == '/docs' ||
        currentPath.startsWith('/docs/');

    int selectedIndex;
    if (isCalendar) {
      selectedIndex = 1;
    } else if (isProfile) {
      selectedIndex = 2;
    } else {
      selectedIndex = 0;
    }

    return NavigationBar(
      labelBehavior: NavigationDestinationLabelBehavior.alwaysHide,
      selectedIndex: selectedIndex,
      onDestinationSelected: (index) {
        switch (index) {
          case 0:
            context.go('/');
          case 1:
            context.go('/calendar');
          case 2:
            context.go('/profile');
        }
      },
      destinations: [
        const NavigationDestination(
          icon: Icon(Icons.eco_outlined),
          selectedIcon: Icon(Icons.eco),
          label: 'home',
        ),
        const NavigationDestination(
          icon: Icon(Icons.calendar_month_outlined),
          selectedIcon: Icon(Icons.calendar_month),
          label: 'calendar',
        ),
        NavigationDestination(
          icon: _profileIcon(user, isProfile),
          selectedIcon: _profileIcon(user, true),
          label: 'profile',
        ),
      ],
    );
  }

  static Widget _profileIcon(User? user, bool selected) {
    if (user != null && user.profilePhotoUrl.isNotEmpty) {
      return ProfileAvatar(
        photoUrl: user.profilePhotoUrl,
        radius: 14,
        selected: selected,
      );
    }
    return selected
        ? const Icon(Icons.person)
        : const Icon(Icons.person_outline);
  }
}
