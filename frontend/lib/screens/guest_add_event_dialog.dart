import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/widgets/phone_form_field.dart';

enum GuestStep { phone, password, pending, unknown }

/// Dialog shown when an unauthenticated user taps the add event FAB.
/// Walks through: phone check → login (if member) or join redirect (if not).
class GuestAddEventDialog extends ConsumerStatefulWidget {
  const GuestAddEventDialog({super.key});

  @override
  ConsumerState<GuestAddEventDialog> createState() =>
      _GuestAddEventDialogState();
}

class _GuestAddEventDialogState extends ConsumerState<GuestAddEventDialog> {
  final _formKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  String _phoneNumber = '';
  GuestStep _step = GuestStep.phone;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _checkPhone() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.post(
        '/api/community/check-phone/',
        data: {'phone_number': _phoneNumber},
      );
      final status = (resp.data as Map<String, dynamic>)['status'] as String;
      if (!mounted) return;
      setState(() {
        _loading = false;
        switch (status) {
          case 'member':
            _step = GuestStep.password;
          case 'pending':
            _step = GuestStep.pending;
          default:
            _step = GuestStep.unknown;
        }
      });
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = ApiError.from(e).message;
          _loading = false;
        });
      }
    }
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .login(_phoneNumber, _passwordController.text);
      if (!mounted) return;
      final authState = ref.read(authProvider);
      if (authState.hasError) {
        setState(() {
          _error = ApiError.from(authState.error!).message;
          _loading = false;
        });
        return;
      }
      // Logged in — signal success to caller, which will open the event form.
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = ApiError.from(e).message;
          _loading = false;
        });
      }
    }
  }

  void _resetToPhone() => setState(() {
    _step = GuestStep.phone;
    _error = null;
    _passwordController.clear();
  });

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('add an event'),
      content: SizedBox(
        width: 360,
        child: Form(
          key: _formKey,
          child: switch (_step) {
            GuestStep.phone => _buildPhoneContent(context),
            GuestStep.password => _buildPasswordContent(context),
            GuestStep.pending => _buildPendingContent(context),
            GuestStep.unknown => _buildUnknownContent(context),
          },
        ),
      ),
      actions: switch (_step) {
        GuestStep.phone => [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('cancel'),
          ),
          FilledButton(
            onPressed: _loading ? null : _checkPhone,
            child: _loading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('continue'),
          ),
        ],
        GuestStep.password => [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('cancel'),
          ),
          TextButton(
            onPressed: _loading ? null : _resetToPhone,
            child: const Text('back'),
          ),
          FilledButton(
            onPressed: _loading ? null : _login,
            child: _loading
                ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                : const Text('log in'),
          ),
        ],
        GuestStep.pending || GuestStep.unknown => [
          TextButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('close'),
          ),
          TextButton(onPressed: _resetToPhone, child: const Text('back')),
        ],
      },
    );
  }

  Widget _buildPhoneContent(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'you need to be logged in to add events — pop in your number and we\'ll sort you out',
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 20),
        PhoneFormField(
          onChanged: (v) => setState(() => _phoneNumber = v),
          textInputAction: TextInputAction.done,
          onFieldSubmitted: (_) => _loading ? null : _checkPhone(),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(
            _error!,
            style: TextStyle(
              color: Theme.of(context).colorScheme.error,
              fontSize: 13,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildPasswordContent(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'welcome back! enter your password to get in',
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 20),
        TextFormField(
          controller: _passwordController,
          decoration: const InputDecoration(
            labelText: 'Password',
            border: OutlineInputBorder(),
          ),
          obscureText: true,
          autofillHints: const [AutofillHints.password],
          validator: (v) => (v == null || v.isEmpty) ? 'Required' : null,
          onFieldSubmitted: (_) => _loading ? null : _login(),
        ),
        if (_error != null) ...[
          const SizedBox(height: 12),
          Text(
            _error!,
            style: TextStyle(
              color: Theme.of(context).colorScheme.error,
              fontSize: 13,
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildPendingContent(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'your request is in review ⏳',
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          "hang tight — we'll be in touch soon",
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
      ],
    );
  }

  Widget _buildUnknownContent(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "we don't recognise that number",
          style: Theme.of(context).textTheme.titleMedium,
        ),
        const SizedBox(height: 8),
        Text(
          'not a member yet? head to the join form and we\'ll sort you out',
          style: TextStyle(
            color: Theme.of(context).colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 16),
        SizedBox(
          width: double.infinity,
          child: OutlinedButton(
            onPressed: () {
              Navigator.of(context).pop();
              context.go('/join');
            },
            child: const Text('request to join'),
          ),
        ),
      ],
    );
  }
}
