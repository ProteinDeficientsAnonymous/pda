import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';

class MagicLoginScreen extends ConsumerStatefulWidget {
  const MagicLoginScreen({super.key, required this.token});

  final String token;

  @override
  ConsumerState<MagicLoginScreen> createState() => _MagicLoginScreenState();
}

class _MagicLoginScreenState extends ConsumerState<MagicLoginScreen> {
  String? _error;

  @override
  void initState() {
    super.initState();
    _doMagicLogin();
  }

  Future<void> _doMagicLogin() async {
    try {
      await ref.read(authProvider.notifier).magicLogin(widget.token);
      // Router redirect handles onboarding navigation once auth state updates.
    } catch (_) {
      if (mounted) {
        setState(
          () => _error =
              'this link is invalid or has expired — ask an admin to resend it',
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_error != null) {
      return Scaffold(
        body: Center(
          child: Padding(
            padding: const EdgeInsets.all(32),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  _error!,
                  textAlign: TextAlign.center,
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
                ),
                const SizedBox(height: 24),
                FilledButton(
                  onPressed: () => context.go('/'),
                  child: const Text('go home'),
                ),
              ],
            ),
          ),
        ),
      );
    }

    return const Scaffold(body: Center(child: Text('signing you in…')));
  }
}
