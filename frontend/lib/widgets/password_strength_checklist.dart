import 'package:flutter/material.dart';

/// Real-time password strength checklist driven by a [TextEditingController].
///
/// Shows four rules with icons that update as the user types.
/// Place below the new-password field; do NOT use on the confirm field.
class PasswordStrengthChecklist extends StatelessWidget {
  final TextEditingController controller;

  const PasswordStrengthChecklist({super.key, required this.controller});

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: controller,
      builder: (context, _) {
        final text = controller.text;
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            _CheckItem(met: text.length >= 12, label: 'at least 12 characters'),
            _CheckItem(
              met: text.isNotEmpty && RegExp(r'[A-Z]').hasMatch(text),
              label: 'one uppercase letter',
            ),
            _CheckItem(
              met: text.isNotEmpty && RegExp(r'[0-9]').hasMatch(text),
              label: 'one number',
            ),
            _CheckItem(
              met: text.isNotEmpty && RegExp(r'[^A-Za-z0-9]').hasMatch(text),
              label: 'one special character',
            ),
          ],
        );
      },
    );
  }
}

class _CheckItem extends StatelessWidget {
  final bool met;
  final String label;

  const _CheckItem({required this.met, required this.label});

  @override
  Widget build(BuildContext context) {
    final color = met
        ? Theme.of(context).colorScheme.primary
        : Theme.of(context).colorScheme.onSurfaceVariant;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 2),
      child: Semantics(
        label: '$label: ${met ? 'met' : 'not met'}',
        excludeSemantics: true,
        child: Row(
          children: [
            Icon(
              met ? Icons.check_circle : Icons.circle_outlined,
              size: 16,
              color: color,
            ),
            const SizedBox(width: 8),
            Text(label, style: TextStyle(fontSize: 13, color: color)),
          ],
        ),
      ),
    );
  }
}
