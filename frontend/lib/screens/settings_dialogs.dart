import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/accessibility_preferences_provider.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/loading_button.dart';
import 'package:pda/widgets/password_strength_checklist.dart';

final _log = Logger('SettingsDialog');

class SettingsEditFieldDialog extends StatefulWidget {
  final String title;
  final String label;
  final String initialValue;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;

  const SettingsEditFieldDialog({
    super.key,
    required this.title,
    required this.label,
    required this.initialValue,
    this.keyboardType = TextInputType.text,
    this.validator,
  });

  @override
  State<SettingsEditFieldDialog> createState() =>
      _SettingsEditFieldDialogState();
}

class _SettingsEditFieldDialogState extends State<SettingsEditFieldDialog> {
  late final TextEditingController _controller;
  final _formKey = GlobalKey<FormState>();

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(text: widget.initialValue);
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(widget.title),
      content: Form(
        key: _formKey,
        child: TextFormField(
          controller: _controller,
          keyboardType: widget.keyboardType,
          autofocus: true,
          textInputAction: TextInputAction.done,
          decoration: InputDecoration(labelText: widget.label),
          validator: widget.validator,
          onFieldSubmitted: (_) {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(_controller.text.trim());
            }
          },
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (_formKey.currentState!.validate()) {
              Navigator.of(context).pop(_controller.text.trim());
            }
          },
          child: const Text('Save'),
        ),
      ],
    );
  }
}

class SettingsChangePasswordDialog extends StatefulWidget {
  final WidgetRef ref;

  const SettingsChangePasswordDialog({super.key, required this.ref});

  @override
  State<SettingsChangePasswordDialog> createState() =>
      _SettingsChangePasswordDialogState();
}

class _SettingsChangePasswordDialogState
    extends State<SettingsChangePasswordDialog> {
  final _formKey = GlobalKey<FormState>();
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  final _newFocus = FocusNode();
  final _confirmFocus = FocusNode();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
    _newFocus.dispose();
    _confirmFocus.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await widget.ref
          .read(authProvider.notifier)
          .changePassword(
            currentPassword: _currentCtrl.text,
            newPassword: _newCtrl.text,
          );
      if (mounted) {
        Navigator.of(context).pop();
        showSnackBar(context, 'password updated ✓');
      }
    } catch (e, st) {
      _log.warning('password change failed', e, st);
      setState(() {
        _error = ApiError.from(e).message;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('change password'),
      content: Form(
        key: _formKey,
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_error != null) ...[
              Text(
                _error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
              const SizedBox(height: 12),
            ],
            TextFormField(
              controller: _currentCtrl,
              obscureText: true,
              autofocus: true,
              textInputAction: TextInputAction.next,
              maxLength: 128,
              decoration: const InputDecoration(labelText: 'Current password'),
              validator: (val) {
                if (val == null || val.isEmpty) return 'Required';
                return null;
              },
              onFieldSubmitted: (_) => _newFocus.requestFocus(),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _newCtrl,
              focusNode: _newFocus,
              obscureText: true,
              textInputAction: TextInputAction.next,
              maxLength: 128,
              decoration: const InputDecoration(labelText: 'New password'),
              validator: v.all([
                v.password(),
                v.maxLength(128),
                (val) => (val != null && val == _currentCtrl.text)
                    ? 'new password must differ from current'
                    : null,
              ]),
              onFieldSubmitted: (_) => _confirmFocus.requestFocus(),
            ),
            const SizedBox(height: 8),
            PasswordStrengthChecklist(controller: _newCtrl),
            const SizedBox(height: 12),
            TextFormField(
              controller: _confirmCtrl,
              focusNode: _confirmFocus,
              obscureText: true,
              textInputAction: TextInputAction.done,
              decoration: const InputDecoration(
                labelText: 'Confirm new password',
              ),
              validator: (val) {
                if (val != _newCtrl.text) return 'Passwords do not match';
                return null;
              },
              onFieldSubmitted: (_) => _loading ? null : _submit(),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        LoadingButton(label: 'Update', onPressed: _submit, loading: _loading),
      ],
    );
  }
}

class SettingsAccessibilitySection extends ConsumerWidget {
  const SettingsAccessibilitySection({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final prefsAsync = ref.watch(accessibilityPreferencesProvider);
    final prefs = prefsAsync.value;
    final dyslexiaOn = prefs?.dyslexiaFriendlyFont ?? false;
    final textScale = prefs?.textScaleFactor ?? 1.0;
    final themeMode = prefs?.themeMode ?? ThemeMode.system;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            const Icon(Icons.brightness_6_outlined, size: 20),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('theme', style: TextStyle(fontSize: 14)),
                  const SizedBox(height: 8),
                  SegmentedButton<ThemeMode>(
                    segments: const [
                      ButtonSegment(
                        value: ThemeMode.system,
                        label: Text('system'),
                      ),
                      ButtonSegment(
                        value: ThemeMode.light,
                        label: Text('light'),
                      ),
                      ButtonSegment(value: ThemeMode.dark, label: Text('dark')),
                    ],
                    selected: {themeMode},
                    showSelectedIcon: false,
                    onSelectionChanged: (selection) {
                      ref
                          .read(accessibilityPreferencesProvider.notifier)
                          .setThemeMode(selection.first);
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
        const SizedBox(height: 16),
        SwitchListTile(
          secondary: const Icon(Icons.text_fields_outlined, size: 20),
          title: const Text(
            'dyslexia-friendly font',
            style: TextStyle(fontSize: 14),
          ),
          value: dyslexiaOn,
          contentPadding: EdgeInsets.zero,
          dense: true,
          onChanged: (_) {
            ref
                .read(accessibilityPreferencesProvider.notifier)
                .toggleDyslexiaFont();
          },
        ),
        const SizedBox(height: 8),
        Row(
          children: [
            const Icon(Icons.format_size_outlined, size: 20),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const Text('text size', style: TextStyle(fontSize: 14)),
                  const SizedBox(height: 8),
                  SegmentedButton<double>(
                    segments: const [
                      ButtonSegment(value: 1.0, label: Text('normal')),
                      ButtonSegment(value: 1.15, label: Text('medium')),
                      ButtonSegment(value: 1.3, label: Text('large')),
                    ],
                    selected: {textScale},
                    showSelectedIcon: false,
                    onSelectionChanged: (selection) {
                      ref
                          .read(accessibilityPreferencesProvider.notifier)
                          .setTextScale(selection.first);
                    },
                  ),
                ],
              ),
            ),
          ],
        ),
      ],
    );
  }
}
