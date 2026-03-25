import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/widgets/app_scaffold.dart';

class HomeScreen extends StatelessWidget {
  const HomeScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      child: SingleChildScrollView(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 800),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 48),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Protein Deficients Anonymous',
                    style: Theme.of(context).textTheme.displaySmall?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                  ),
                  const SizedBox(height: 8),
                  Text(
                    'A collective liberation community',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          color: Colors.grey[600],
                        ),
                  ),
                  const SizedBox(height: 48),
                  Text(
                    'Who we are',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'Protein Deficients Anonymous (PDA) is a vegan community grounded in collective liberation. '
                    'We believe that the liberation of animals, humans, and the earth are deeply interconnected. '
                    'We organize, share resources, and build solidarity across movements.',
                    style: TextStyle(fontSize: 16, height: 1.6),
                  ),
                  const SizedBox(height: 48),
                  Text(
                    'Our values',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 16),
                  ...[
                    ('🌱', 'Collective liberation', 'Animal liberation and human liberation are inseparable.'),
                    ('🤝', 'Mutual aid', 'We support each other materially, not just ideologically.'),
                    ('🌍', 'Intersectionality', 'We center those most impacted by systems of oppression.'),
                    ('✊', 'Direct action', 'We take action in the world, not just in conversation.'),
                  ].map(
                    (v) => Padding(
                      padding: const EdgeInsets.only(bottom: 20),
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(v.$1, style: const TextStyle(fontSize: 28)),
                          const SizedBox(width: 16),
                          Expanded(
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text(
                                  v.$2,
                                  style: const TextStyle(
                                    fontSize: 16,
                                    fontWeight: FontWeight.bold,
                                  ),
                                ),
                                const SizedBox(height: 4),
                                Text(v.$3, style: const TextStyle(fontSize: 15, height: 1.5)),
                              ],
                            ),
                          ),
                        ],
                      ),
                    ),
                  ),
                  const SizedBox(height: 48),
                  Text(
                    'Want to join us?',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 16),
                  const Text(
                    'PDA is a vetted community. We review join requests to ensure alignment with our values '
                    'and capacity to welcome new members. Fill out the form below to request membership.',
                    style: TextStyle(fontSize: 16, height: 1.6),
                  ),
                  const SizedBox(height: 24),
                  ElevatedButton(
                    onPressed: () => context.go('/join'),
                    style: ElevatedButton.styleFrom(
                      padding: const EdgeInsets.symmetric(horizontal: 32, vertical: 16),
                    ),
                    child: const Text('Request to join', style: TextStyle(fontSize: 16)),
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}
