import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

class WhatsAppSetupInstructions extends StatefulWidget {
  const WhatsAppSetupInstructions({super.key});

  @override
  State<WhatsAppSetupInstructions> createState() =>
      _WhatsAppSetupInstructionsState();
}

class _WhatsAppSetupInstructionsState extends State<WhatsAppSetupInstructions> {
  bool _expanded = false;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerLow,
        borderRadius: BorderRadius.circular(8),
        border: Border.all(color: theme.colorScheme.outlineVariant),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          InkWell(
            borderRadius: BorderRadius.circular(8),
            onTap: () => setState(() => _expanded = !_expanded),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
              child: Row(
                children: [
                  Icon(
                    Icons.menu_book_outlined,
                    size: 18,
                    color: theme.colorScheme.primary,
                  ),
                  const SizedBox(width: 10),
                  Text(
                    'Setup instructions',
                    style: theme.textTheme.titleSmall?.copyWith(
                      color: theme.colorScheme.primary,
                    ),
                  ),
                  const Spacer(),
                  Icon(
                    _expanded ? Icons.expand_less : Icons.expand_more,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ],
              ),
            ),
          ),
          if (_expanded)
            Padding(
              padding: const EdgeInsets.fromLTRB(16, 0, 16, 16),
              child: _SetupInstructionsBody(theme: theme),
            ),
        ],
      ),
    );
  }
}

class _SetupInstructionsBody extends StatelessWidget {
  const _SetupInstructionsBody({required this.theme});

  final ThemeData theme;

  @override
  Widget build(BuildContext context) {
    return SelectionArea(
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Divider(),
          const SizedBox(height: 8),
          _step(
            theme,
            '1',
            'Get a dedicated phone number',
            'The bot needs its own WhatsApp account — use a SIM you don\'t mind '
                'dedicating to this. A cheap prepaid SIM works fine.',
          ),
          _step(
            theme,
            '2',
            'Run the bot',
            'In the whatsapp-bot/ directory:',
            code: 'node index.js',
            codeLabel: 'start bot',
          ),
          _step(
            theme,
            '3',
            'Scan the QR code',
            'The bot prints a QR code in the terminal on first run. Open WhatsApp '
                'on the bot phone → Linked devices → Link a device, then scan it. '
                'Credentials are saved to auth_info/ so you only do this once.',
          ),
          _step(
            theme,
            '4',
            'Add the bot to your group',
            'Add the bot\'s phone number to the WhatsApp group as you would any contact.',
          ),
          _step(
            theme,
            '5',
            'Find the group ID',
            'Once connected, the bot logs all joined groups on startup:',
            code:
                'Joined groups (copy the JID you want as WHATSAPP_GROUP_ID):\n'
                '  120363XXXXXXXXXX@g.us  —  PDA members',
            codeLabel: 'copy group JID',
          ),
          _step(
            theme,
            '6',
            'Set a bot secret',
            'Pick any random string as a shared secret — this stops unauthorized '
                'callers from posting to your group. Set it as the BOT_SECRET '
                'environment variable when running the bot:',
            code: 'BOT_SECRET=your-secret node index.js',
            codeLabel: 'run with secret',
          ),
          _step(
            theme,
            '7',
            'Enter the config here',
            'Fill in the Bot URL (where the bot is reachable from the Django server), '
                'the secret, and the group ID above, then hit Save. '
                'Use the Refresh button to confirm the bot shows as connected.',
            isLast: true,
          ),
        ],
      ),
    );
  }

  Widget _step(
    ThemeData theme,
    String number,
    String title,
    String body, {
    String? code,
    String? codeLabel,
    bool isLast = false,
  }) {
    return Padding(
      padding: EdgeInsets.only(bottom: isLast ? 0 : 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Container(
            width: 24,
            height: 24,
            decoration: BoxDecoration(
              color: theme.colorScheme.primaryContainer,
              shape: BoxShape.circle,
            ),
            alignment: Alignment.center,
            child: Text(
              number,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.bold,
                color: theme.colorScheme.onPrimaryContainer,
              ),
            ),
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  title,
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontWeight: FontWeight.w600,
                  ),
                ),
                const SizedBox(height: 2),
                Text(
                  body,
                  style: TextStyle(
                    fontSize: 13,
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
                if (code != null) ...[
                  const SizedBox(height: 8),
                  WhatsAppCodeBlock(code: code, label: codeLabel),
                ],
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class WhatsAppCodeBlock extends StatelessWidget {
  const WhatsAppCodeBlock({super.key, required this.code, this.label});

  final String code;
  final String? label;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.surfaceContainerHighest,
        borderRadius: BorderRadius.circular(6),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Expanded(
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
              child: Text(
                code,
                style: const TextStyle(
                  fontFamily: 'monospace',
                  fontSize: 12,
                  height: 1.5,
                ),
              ),
            ),
          ),
          Tooltip(
            message: label ?? 'Copy',
            child: IconButton(
              icon: const Icon(Icons.copy_outlined, size: 16),
              onPressed: () {
                Clipboard.setData(ClipboardData(text: code));
                ScaffoldMessenger.of(context).showSnackBar(
                  const SnackBar(
                    content: Text('Copied'),
                    duration: Duration(seconds: 1),
                  ),
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}
