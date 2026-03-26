import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/app_scaffold.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).valueOrNull;

    return AppScaffold(
      child: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          // Profile photo
          Center(
            child: Stack(
              children: [
                CircleAvatar(
                  radius: 48,
                  backgroundColor:
                      Theme.of(context).colorScheme.primaryContainer,
                  child: Text(
                    _initials(user?.displayName, user?.email),
                    style: TextStyle(
                      fontSize: 28,
                      fontWeight: FontWeight.bold,
                      color: Theme.of(context).colorScheme.onPrimaryContainer,
                    ),
                  ),
                ),
                Positioned(
                  bottom: 0,
                  right: 0,
                  child: Tooltip(
                    message: 'Coming soon',
                    child: CircleAvatar(
                      radius: 16,
                      backgroundColor: Theme.of(context).colorScheme.surface,
                      child: Icon(
                        Icons.camera_alt_outlined,
                        size: 16,
                        color: Theme.of(context).colorScheme.onSurfaceVariant,
                      ),
                    ),
                  ),
                ),
              ],
            ),
          ),
          const SizedBox(height: 32),
          Text(
            'Profile',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          _SettingsTile(
            icon: Icons.person_outline,
            label: 'Name',
            value:
                (user?.displayName ?? '').trim().isEmpty
                    ? 'Not set'
                    : user!.displayName,
            onTap: () => _showEditNameDialog(context, ref, user?.displayName),
          ),
          _SettingsTile(
            icon: Icons.phone_outlined,
            label: 'Phone',
            value: user?.phoneNumber ?? '',
          ),
          _SettingsTile(
            icon: Icons.email_outlined,
            label: 'Email',
            value: (user?.email ?? '').trim().isEmpty ? 'Not set' : user!.email,
            onTap: () => _showEditEmailDialog(context, ref, user?.email),
          ),
          const SizedBox(height: 24),
          Text(
            'Security',
            style: Theme.of(context).textTheme.labelLarge?.copyWith(
              color: Theme.of(context).colorScheme.primary,
            ),
          ),
          const SizedBox(height: 12),
          _SettingsTile(
            icon: Icons.lock_outline,
            label: 'Change password',
            onTap: () => _showChangePasswordDialog(context, ref),
          ),
        ],
      ),
    );
  }

  String _initials(String? displayName, String? email) {
    if (displayName != null && displayName.isNotEmpty) {
      final parts = displayName.trim().split(RegExp(r'\s+'));
      final f = parts.first[0].toUpperCase();
      final l = parts.length > 1 ? parts.last[0].toUpperCase() : '';
      return '$f$l';
    }
    if (email != null && email.isNotEmpty) return email[0].toUpperCase();
    return '?';
  }

  Future<void> _showEditNameDialog(
    BuildContext context,
    WidgetRef ref,
    String? current,
  ) async {
    final result = await showDialog<String>(
      context: context,
      builder:
          (_) => _EditFieldDialog(
            title: 'Edit name',
            label: 'Display name',
            initialValue: current ?? '',
            keyboardType: TextInputType.name,
            validator: v.displayName(),
          ),
    );
    if (result == null || !context.mounted) return;
    try {
      await ref.read(authProvider.notifier).updateProfile(displayName: result);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Name updated')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(ApiError.from(e).message)));
      }
    }
  }

  Future<void> _showEditEmailDialog(
    BuildContext context,
    WidgetRef ref,
    String? current,
  ) async {
    final result = await showDialog<String>(
      context: context,
      builder:
          (_) => _EditFieldDialog(
            title: 'Edit email',
            label: 'Email address',
            initialValue: current ?? '',
            keyboardType: TextInputType.emailAddress,
            validator: v.optionalEmail(),
          ),
    );
    if (result == null || !context.mounted) return;
    try {
      await ref.read(authProvider.notifier).updateProfile(email: result);
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Email updated')));
      }
    } catch (e) {
      if (context.mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(ApiError.from(e).message)));
      }
    }
  }

  Future<void> _showChangePasswordDialog(
    BuildContext context,
    WidgetRef ref,
  ) async {
    await showDialog<void>(
      context: context,
      builder: (_) => _ChangePasswordDialog(ref: ref),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String label;
  final String? value;
  final VoidCallback? onTap;

  const _SettingsTile({
    required this.icon,
    required this.label,
    this.value,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(
          icon,
          color: Theme.of(context).colorScheme.onSurfaceVariant,
        ),
        title: Text(label),
        subtitle: value != null ? Text(value!) : null,
        trailing: onTap != null ? const Icon(Icons.chevron_right) : null,
        onTap: onTap,
      ),
    );
  }
}

class _EditFieldDialog extends StatefulWidget {
  final String title;
  final String label;
  final String initialValue;
  final TextInputType keyboardType;
  final String? Function(String?)? validator;

  const _EditFieldDialog({
    required this.title,
    required this.label,
    required this.initialValue,
    this.keyboardType = TextInputType.text,
    this.validator,
  });

  @override
  State<_EditFieldDialog> createState() => _EditFieldDialogState();
}

class _EditFieldDialogState extends State<_EditFieldDialog> {
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
          decoration: InputDecoration(labelText: widget.label),
          validator: widget.validator,
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

class _ChangePasswordDialog extends StatefulWidget {
  final WidgetRef ref;

  const _ChangePasswordDialog({required this.ref});

  @override
  State<_ChangePasswordDialog> createState() => _ChangePasswordDialogState();
}

class _ChangePasswordDialogState extends State<_ChangePasswordDialog> {
  final _formKey = GlobalKey<FormState>();
  final _currentCtrl = TextEditingController();
  final _newCtrl = TextEditingController();
  final _confirmCtrl = TextEditingController();
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _currentCtrl.dispose();
    _newCtrl.dispose();
    _confirmCtrl.dispose();
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
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Password updated')));
      }
    } catch (e) {
      setState(() {
        _error = ApiError.from(e).message;
        _loading = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Change password'),
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
              decoration: const InputDecoration(labelText: 'Current password'),
              validator: (v) {
                if (v == null || v.isEmpty) return 'Required';
                return null;
              },
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _newCtrl,
              obscureText: true,
              decoration: const InputDecoration(labelText: 'New password'),
              validator: v.all([
                v.required(),
                (val) =>
                    (val != null && val.length < 8)
                        ? 'Must be at least 8 characters'
                        : null,
                (val) =>
                    (val != null && val.length > 128)
                        ? 'Max 128 characters'
                        : null,
                (val) =>
                    (val != null && val == _currentCtrl.text)
                        ? 'New password must differ from current'
                        : null,
              ]),
            ),
            const SizedBox(height: 12),
            TextFormField(
              controller: _confirmCtrl,
              obscureText: true,
              decoration: const InputDecoration(
                labelText: 'Confirm new password',
              ),
              validator: (v) {
                if (v != _newCtrl.text) return 'Passwords do not match';
                return null;
              },
            ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: _loading ? null : () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _loading ? null : _submit,
          child:
              _loading
                  ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                  : const Text('Update'),
        ),
      ],
    );
  }
}
