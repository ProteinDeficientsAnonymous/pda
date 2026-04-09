import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:pda/utils/launcher_stub.dart';
import 'package:pda/utils/snackbar.dart';

/// Displays a magic login link after a user account is created or a join
/// request is approved.
class ApprovalCredentialsDialog extends StatelessWidget {
  const ApprovalCredentialsDialog({
    super.key,
    required this.title,
    required this.body,
    required this.magicLinkToken,
    this.phoneNumber,
  });

  final String title;
  final String body;
  final String magicLinkToken;

  /// If provided, a phone row is shown above the link field and the button
  /// will open the native SMS app instead of copying to clipboard.
  final String? phoneNumber;

  String get _loginUrl {
    final origin = Uri.base.origin;
    return '$origin/magic-login/$magicLinkToken';
  }

  @override
  Widget build(BuildContext context) {
    final url = _loginUrl;
    final phone = phoneNumber;
    return AlertDialog(
      title: Text(title),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(body),
          const SizedBox(height: 12),
          if (phone != null) ...[
            _LabeledRow(label: 'phone', value: phone),
            const SizedBox(height: 12),
          ],
          const Text(
            'login link',
            style: TextStyle(fontSize: 12, color: Colors.grey),
          ),
          const SizedBox(height: 4),
          MagicLinkField(url: url),
          const SizedBox(height: 12),
          _WelcomeMessageButton(url: url, phoneNumber: phone),
          const SizedBox(height: 8),
          Text(
            'includes login link — expires in 7 days',
            style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
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

/// Button that opens the native SMS app with the welcome message pre-filled,
/// or falls back to clipboard copy if no phone number is available or if the
/// SMS app cannot be launched.
class _WelcomeMessageButton extends StatelessWidget {
  const _WelcomeMessageButton({required this.url, this.phoneNumber});

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
      showSnackBar(context, 'welcome message copied ✓');
    }
  }

  @override
  Widget build(BuildContext context) {
    final haPhone = phoneNumber != null;
    return OutlinedButton.icon(
      onPressed: () => _handleTap(context),
      icon: Icon(
        haPhone ? Icons.sms_outlined : Icons.content_copy_outlined,
        size: 16,
      ),
      label: Text(haPhone ? 'text welcome message' : 'copy welcome message'),
    );
  }
}

/// Displays a magic link URL with a copy-to-clipboard icon button.
/// Public so it can be reused in other dialogs (e.g. add member flow).
class MagicLinkField extends StatelessWidget {
  final String url;

  const MagicLinkField({super.key, required this.url});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(6),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              url,
              style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: () {
              Clipboard.setData(ClipboardData(text: url));
            },
            borderRadius: BorderRadius.circular(4),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Icon(
                Icons.content_copy_outlined,
                size: 16,
                color: Colors.grey.shade600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _LabeledRow extends StatelessWidget {
  final String label;
  final String value;

  const _LabeledRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Text(
          '$label: ',
          style: const TextStyle(fontSize: 13, color: Colors.grey),
        ),
        Text(
          value,
          style: const TextStyle(fontSize: 13, fontWeight: FontWeight.w600),
        ),
      ],
    );
  }
}
