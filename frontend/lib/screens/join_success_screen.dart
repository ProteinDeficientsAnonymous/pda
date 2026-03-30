import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/widgets/app_scaffold.dart';

class JoinSuccessScreen extends StatelessWidget {
  const JoinSuccessScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 600),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 64),
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.check_circle, size: 72, color: Colors.green),
                const SizedBox(height: 24),
                Text(
                  'request received! 🌱',
                  style: Theme.of(context).textTheme.headlineMedium,
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 16),
                const Text(
                  'thanks for reaching out — a member of our vetting group will review your request '
                  'and get back to you',
                  style: TextStyle(fontSize: 16, height: 1.6),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 32),
                TextButton(
                  onPressed: () => context.go('/'),
                  child: const Text('back to home'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}
