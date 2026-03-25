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
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 56),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _HeroSection(),
                  const SizedBox(height: 64),
                  _SectionDivider(),
                  const SizedBox(height: 64),
                  _WhoWeAreSection(),
                  const SizedBox(height: 64),
                  _SectionDivider(),
                  const SizedBox(height: 64),
                  _ValuesSection(),
                  const SizedBox(height: 64),
                  _SectionDivider(),
                  const SizedBox(height: 64),
                  _HowItWorksSection(),
                  const SizedBox(height: 64),
                  _SectionDivider(),
                  const SizedBox(height: 64),
                  _JoinSection(),
                  const SizedBox(height: 48),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _HeroSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'Protein Deficients Anonymous',
          style: theme.textTheme.displaySmall?.copyWith(
            fontWeight: FontWeight.bold,
            color: colorScheme.onSurface,
          ),
        ),
        const SizedBox(height: 16),
        Text(
          'Liberation is not a single-issue struggle.',
          style: theme.textTheme.headlineSmall?.copyWith(
            color: colorScheme.primary,
            fontWeight: FontWeight.w500,
          ),
        ),
        const SizedBox(height: 20),
        Text(
          'We are a vetted community of vegans committed to collective liberation — '
          'building solidarity across movements, showing up for each other, '
          'and working toward a world free from all forms of domination.',
          style: theme.textTheme.bodyLarge?.copyWith(
            height: 1.7,
            color: colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 32),
        _JoinButton(),
      ],
    );
  }
}

class _WhoWeAreSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Who we are', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 16),
        Text(
          'Protein Deficients Anonymous (PDA) is a vegan community grounded in collective liberation. '
          'We believe that the liberation of animals, humans, and the earth are deeply interconnected. '
          'We organize, share resources, and build solidarity across movements.',
          style: theme.textTheme.bodyLarge?.copyWith(height: 1.7),
        ),
      ],
    );
  }
}

class _ValuesSection extends StatelessWidget {
  static const _values = [
    (
      '🌱',
      'Collective liberation',
      'Animal liberation and human liberation are inseparable.',
    ),
    (
      '🤝',
      'Mutual aid',
      'We support each other materially, not just ideologically.',
    ),
    (
      '🌍',
      'Intersectionality',
      'We center those most impacted by systems of oppression.',
    ),
    (
      '✊',
      'Direct action',
      'We take action in the world, not just in conversation.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('Our values', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 24),
        ...(_values.map((v) => _ValueItem(
              emoji: v.$1,
              title: v.$2,
              description: v.$3,
              colorScheme: colorScheme,
              theme: theme,
            ))),
      ],
    );
  }
}

class _ValueItem extends StatelessWidget {
  final String emoji;
  final String title;
  final String description;
  final ColorScheme colorScheme;
  final ThemeData theme;

  const _ValueItem({
    required this.emoji,
    required this.title,
    required this.description,
    required this.colorScheme,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: colorScheme.surfaceContainerLowest,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colorScheme.outlineVariant),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(emoji, style: const TextStyle(fontSize: 28)),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: theme.textTheme.titleMedium?.copyWith(
                      fontWeight: FontWeight.bold,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: theme.textTheme.bodyMedium?.copyWith(
                      height: 1.5,
                      color: colorScheme.onSurfaceVariant,
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _HowItWorksSection extends StatelessWidget {
  static const _steps = [
    (
      '1',
      'Submit a request',
      'Fill out a short form telling us about yourself, your values, '
          'and why you want to be part of PDA.',
    ),
    (
      '2',
      'We review it together',
      'Your request goes to our vetting group. We read every submission carefully '
          'and discuss as a community.',
    ),
    (
      '3',
      'You hear back from us',
      'If it feels like a good fit, we will reach out to welcome you in. '
          'Either way, we will let you know.',
    ),
  ];

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('What to expect', style: theme.textTheme.headlineMedium),
        const SizedBox(height: 8),
        Text(
          'PDA is a vetted community. Here is how the process works.',
          style: theme.textTheme.bodyLarge?.copyWith(
            color: colorScheme.onSurfaceVariant,
            height: 1.6,
          ),
        ),
        const SizedBox(height: 24),
        ...(_steps.map((s) => _StepItem(
              number: s.$1,
              title: s.$2,
              description: s.$3,
              colorScheme: colorScheme,
              theme: theme,
            ))),
      ],
    );
  }
}

class _StepItem extends StatelessWidget {
  final String number;
  final String title;
  final String description;
  final ColorScheme colorScheme;
  final ThemeData theme;

  const _StepItem({
    required this.number,
    required this.title,
    required this.description,
    required this.colorScheme,
    required this.theme,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 36,
            height: 36,
            decoration: BoxDecoration(
              color: colorScheme.primaryContainer,
              shape: BoxShape.circle,
            ),
            child: Center(
              child: Text(
                number,
                style: theme.textTheme.titleMedium?.copyWith(
                  color: colorScheme.onPrimaryContainer,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.titleMedium?.copyWith(
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 4),
                Text(
                  description,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    height: 1.6,
                    color: colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _JoinSection extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final colorScheme = theme.colorScheme;

    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(32),
      decoration: BoxDecoration(
        color: colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(16),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Ready to get involved?',
            style: theme.textTheme.headlineSmall?.copyWith(
              fontWeight: FontWeight.bold,
              color: colorScheme.onPrimaryContainer,
            ),
          ),
          const SizedBox(height: 12),
          Text(
            'If our values resonate with you, we would love to hear from you. '
            'Membership is not a transaction — it is a commitment to showing up.',
            style: theme.textTheme.bodyLarge?.copyWith(
              height: 1.6,
              color: colorScheme.onPrimaryContainer,
            ),
          ),
          const SizedBox(height: 24),
          _JoinButton(),
        ],
      ),
    );
  }
}

class _JoinButton extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return FilledButton(
      onPressed: () => context.go('/join'),
      style: FilledButton.styleFrom(
        padding: const EdgeInsets.symmetric(horizontal: 36, vertical: 18),
        textStyle: const TextStyle(fontSize: 16, fontWeight: FontWeight.w600),
      ),
      child: const Text('Request to join'),
    );
  }
}

class _SectionDivider extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Divider(
      color: Theme.of(context).colorScheme.outlineVariant,
      thickness: 1,
    );
  }
}
