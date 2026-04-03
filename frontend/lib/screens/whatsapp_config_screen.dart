import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/whatsapp_config_provider.dart';
import 'package:pda/screens/whatsapp_setup_instructions.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';

class WhatsAppConfigScreen extends ConsumerWidget {
  const WhatsAppConfigScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return const AppScaffold(child: _WhatsAppConfigBody());
  }
}

class _WhatsAppConfigBody extends ConsumerWidget {
  const _WhatsAppConfigBody();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final configAsync = ref.watch(whatsAppConfigProvider);

    return configAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (e, _) => Center(
        child: Text('Failed to load config: ${ApiError.from(e).message}'),
      ),
      data: (config) => _WhatsAppConfigForm(config: config),
    );
  }
}

class _WhatsAppConfigForm extends ConsumerStatefulWidget {
  final WhatsAppConfig config;

  const _WhatsAppConfigForm({required this.config});

  @override
  ConsumerState<_WhatsAppConfigForm> createState() =>
      _WhatsAppConfigFormState();
}

class _WhatsAppConfigFormState extends ConsumerState<_WhatsAppConfigForm> {
  late final TextEditingController _botUrlCtrl;
  late final TextEditingController _secretCtrl;
  late final TextEditingController _groupIdCtrl;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _botUrlCtrl = TextEditingController(text: widget.config.botUrl);
    _secretCtrl = TextEditingController();
    _groupIdCtrl = TextEditingController(text: widget.config.groupId);
  }

  @override
  void dispose() {
    _botUrlCtrl.dispose();
    _secretCtrl.dispose();
    _groupIdCtrl.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      await ref
          .read(whatsAppConfigProvider.notifier)
          .save(
            botUrl: _botUrlCtrl.text.trim(),
            botSecret: _secretCtrl.text.isEmpty ? null : _secretCtrl.text,
            groupId: _groupIdCtrl.text.trim(),
          );
      _secretCtrl.clear();
      if (mounted) showSnackBar(context, 'Saved');
    } catch (e) {
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final statusAsync = ref.watch(whatsAppStatusProvider);
    final theme = Theme.of(context);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 560),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'WhatsApp configuration',
              style: theme.textTheme.headlineSmall,
            ),
            const SizedBox(height: 4),
            Text(
              'Configure the WhatsApp bot that posts event notifications to the group.',
              style: TextStyle(color: theme.colorScheme.onSurfaceVariant),
            ),
            const SizedBox(height: 24),
            const WhatsAppSetupInstructions(),
            const SizedBox(height: 32),
            _StatusCard(statusAsync: statusAsync),
            const SizedBox(height: 32),
            Text('Bot settings', style: theme.textTheme.titleMedium),
            const SizedBox(height: 16),
            TextField(
              controller: _botUrlCtrl,
              decoration: const InputDecoration(
                labelText: 'Bot URL',
                hintText: 'http://localhost:3001',
                border: OutlineInputBorder(),
                helperText: 'The URL of the WhatsApp bot microservice.',
              ),
              keyboardType: TextInputType.url,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _secretCtrl,
              decoration: InputDecoration(
                labelText: 'Bot secret',
                hintText: widget.config.hasSecret
                    ? '••••••••  (leave blank to keep current)'
                    : 'Enter secret',
                border: const OutlineInputBorder(),
                helperText: 'The X-Bot-Secret header value.',
              ),
              obscureText: true,
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _groupIdCtrl,
              decoration: const InputDecoration(
                labelText: 'Group ID',
                hintText: '1234567890@g.us',
                border: OutlineInputBorder(),
                helperText:
                    'The WhatsApp group JID (shown in bot logs on startup).',
              ),
            ),
            const SizedBox(height: 24),
            FilledButton(
              onPressed: _saving ? null : _save,
              child: _saving
                  ? const SizedBox(
                      width: 18,
                      height: 18,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Text('Save'),
            ),
          ],
        ),
      ),
    );
  }
}

class _StatusCard extends ConsumerWidget {
  const _StatusCard({required this.statusAsync});

  final AsyncValue<bool> statusAsync;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);

    final (icon, label, color) = statusAsync.when(
      loading: () => (
        const SizedBox(
              width: 16,
              height: 16,
              child: CircularProgressIndicator(strokeWidth: 2),
            )
            as Widget,
        'Checking…',
        theme.colorScheme.onSurfaceVariant,
      ),
      error: (_, __) => (
        Icon(Icons.error_outline, size: 18, color: theme.colorScheme.error)
            as Widget,
        'Could not reach bot',
        theme.colorScheme.error,
      ),
      data: (connected) => connected
          ? (
              Icon(
                    Icons.check_circle_outline,
                    size: 18,
                    color: Colors.green.shade600,
                  )
                  as Widget,
              'Bot connected',
              Colors.green.shade600,
            )
          : (
              Icon(
                    Icons.cancel_outlined,
                    size: 18,
                    color: theme.colorScheme.error,
                  )
                  as Widget,
              'Bot not connected',
              theme.colorScheme.error,
            ),
    );

    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      decoration: BoxDecoration(
        border: Border.all(color: theme.colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        children: [
          icon,
          const SizedBox(width: 10),
          Text(
            label,
            style: TextStyle(color: color, fontWeight: FontWeight.w500),
          ),
          const Spacer(),
          TextButton(
            onPressed: () => ref.invalidate(whatsAppStatusProvider),
            child: const Text('Refresh'),
          ),
        ],
      ),
    );
  }
}
