import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:pda/utils/launcher_stub.dart';
import 'package:pda/utils/snackbar.dart';

/// Displays a magic login link after a user account is created or a join
/// request is approved. Shows a single button to send the link via SMS,
/// falling back to clipboard copy if SMS is unavailable.
class ApprovalCredentialsDialog extends StatelessWidget {
  const ApprovalCredentialsDialog({
    super.key,
    required this.title,
    required this.magicLinkToken,
    this.phoneNumber,
    this.body,
  });

  final String title;
  final String magicLinkToken;
  final String? phoneNumber;
  final String? body;

  String get _loginUrl {
    final origin = Uri.base.origin;
    return '$origin/magic-login/$magicLinkToken';
  }

  @override
  Widget build(BuildContext context) {
    final url = _loginUrl;
    final phone = phoneNumber;
    return AlertDialog(
      title: Text(title, textAlign: TextAlign.center),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.center,
        children: [
          if (body != null) ...[Text(body!), const SizedBox(height: 16)],
          _CopyLinkButton(url: url),
          const SizedBox(height: 8),
          _SendMessageButton(url: url, phoneNumber: phone),
          const SizedBox(height: 8),
          Text(
            'link expires in 7 days',
            style: TextStyle(
              color: Theme.of(context).colorScheme.outline,
              fontSize: 12,
            ),
          ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('done'),
        ),
      ],
    );
  }
}

class _CopyLinkButton extends StatelessWidget {
  const _CopyLinkButton({required this.url});

  final String url;

  @override
  Widget build(BuildContext context) {
    return FilledButton.icon(
      onPressed: () {
        Clipboard.setData(ClipboardData(text: url));
        showSnackBar(context, 'link copied ✓');
      },
      icon: const Icon(Icons.copy, size: 16),
      label: const Text('copy link'),
    );
  }
}

class _SendMessageButton extends StatelessWidget {
  const _SendMessageButton({required this.url, this.phoneNumber});

  final String url;
  final String? phoneNumber;

  String get _message =>
      "hey! you've been added to PDA 🌱\n\n"
      'click here to log in: $url\n\n'
      'the link works once and expires in 7 days — '
      "you'll set your password on first login";

  Future<void> _handleTap(BuildContext context) async {
    final phone = phoneNumber;
    if (phone != null) {
      final launched = await sendSms(phoneNumber: phone, body: _message);
      if (!context.mounted) return;
      if (!launched) {
        Clipboard.setData(ClipboardData(text: _message));
        showSnackBar(
          context,
          "couldn't open texting app — message copied instead",
        );
      }
    } else {
      Clipboard.setData(ClipboardData(text: _message));
      showSnackBar(context, 'message copied ✓');
    }
  }

  @override
  Widget build(BuildContext context) {
    return OutlinedButton.icon(
      onPressed: () => _handleTap(context),
      icon: const Icon(Icons.send, size: 16),
      label: const Text('send message'),
    );
  }
}
