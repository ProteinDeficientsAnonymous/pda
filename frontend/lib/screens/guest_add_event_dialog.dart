import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/widgets/phone_form_field.dart';

enum GuestStep { phone, password }

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
      if (status == 'member') {
        setState(() {
          _step = GuestStep.password;
          _loading = false;
        });
      } else {
        Navigator.of(context).pop();
        context.go('/join');
      }
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

  @override
  Widget build(BuildContext context) {
    final isPhone = _step == GuestStep.phone;

    return AlertDialog(
      title: const Text('add an event'),
      content: SizedBox(
        width: 360,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isPhone
                    ? 'you need to be logged in to add events — pop in your number and we\'ll sort you out'
                    : 'welcome back! enter your password to get in',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 20),
              if (isPhone)
                PhoneFormField(
                  onChanged: (v) => setState(() => _phoneNumber = v),
                  helperText:
                      'not a member yet? we\'ll send you to the join form',
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _loading ? null : _checkPhone(),
                )
              else
                TextFormField(
                  controller: _passwordController,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                  ),
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  validator:
                      (v) => (v == null || v.isEmpty) ? 'Required' : null,
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
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        if (_step == GuestStep.password)
          TextButton(
            onPressed:
                _loading
                    ? null
                    : () => setState(() {
                      _step = GuestStep.phone;
                      _error = null;
                    }),
            child: const Text('back'),
          ),
        FilledButton(
          onPressed: _loading ? null : (isPhone ? _checkPhone : _login),
          child:
              _loading
                  ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                  : Text(isPhone ? 'continue' : 'log in'),
        ),
      ],
    );
  }
}
