import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/password_strength_checklist.dart';

final _log = Logger('Onboarding');

class OnboardingScreen extends ConsumerStatefulWidget {
  const OnboardingScreen({super.key});

  @override
  ConsumerState<OnboardingScreen> createState() => _OnboardingScreenState();
}

class _OnboardingScreenState extends ConsumerState<OnboardingScreen> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameCtrl = TextEditingController();
  final _emailCtrl = TextEditingController();
  final _newPwCtrl = TextEditingController();
  final _confirmPwCtrl = TextEditingController();
  final _emailFocusNode = FocusNode();
  final _newPwFocusNode = FocusNode();
  final _confirmPwFocusNode = FocusNode();
  bool _saving = false;
  bool _obscureNew = true;
  bool _obscureConfirm = true;

  @override
  void dispose() {
    _displayNameCtrl.dispose();
    _emailCtrl.dispose();
    _newPwCtrl.dispose();
    _confirmPwCtrl.dispose();
    _emailFocusNode.dispose();
    _newPwFocusNode.dispose();
    _confirmPwFocusNode.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await ref
          .read(authProvider.notifier)
          .completeOnboarding(
            displayName: _displayNameCtrl.text.trim(),
            email: _emailCtrl.text.trim().isEmpty
                ? null
                : _emailCtrl.text.trim(),
            newPassword: _newPwCtrl.text,
          );
      // Router redirect will navigate to /guidelines once needsOnboarding becomes false.
      _log.info('onboarding completed');
    } catch (e, st) {
      _log.warning('onboarding failed', e, st);
      if (!mounted) return;
      showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AppScaffold(
      child: Center(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 440),
            child: Card(
              elevation: 2,
              child: Padding(
                padding: const EdgeInsets.all(32),
                child: Form(
                  key: _formKey,
                  child: Column(
                    mainAxisSize: MainAxisSize.min,
                    crossAxisAlignment: CrossAxisAlignment.stretch,
                    children: [
                      Text(
                        'welcome! let\'s get you set up 🎉',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'choose a display name and a new password to get started',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.onSurfaceVariant,
                        ),
                      ),
                      const SizedBox(height: 24),
                      TextFormField(
                        controller: _displayNameCtrl,
                        decoration: const InputDecoration(
                          labelText: 'what should we call you?',
                        ),
                        textInputAction: TextInputAction.next,
                        onFieldSubmitted: (_) => _emailFocusNode.requestFocus(),
                        validator: v.displayName(),
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _emailCtrl,
                        focusNode: _emailFocusNode,
                        decoration: const InputDecoration(
                          labelText: 'email (optional)',
                        ),
                        keyboardType: TextInputType.emailAddress,
                        textInputAction: TextInputAction.next,
                        onFieldSubmitted: (_) => _newPwFocusNode.requestFocus(),
                        validator: v.optionalEmail(),
                      ),
                      const SizedBox(height: 20),
                      TextFormField(
                        controller: _newPwCtrl,
                        focusNode: _newPwFocusNode,
                        obscureText: _obscureNew,
                        decoration: InputDecoration(
                          labelText: 'create a password',
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureNew
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                            tooltip: _obscureNew
                                ? 'Show password'
                                : 'Hide password',
                            onPressed: () =>
                                setState(() => _obscureNew = !_obscureNew),
                          ),
                        ),
                        maxLength: 128,
                        textInputAction: TextInputAction.next,
                        onFieldSubmitted: (_) =>
                            _confirmPwFocusNode.requestFocus(),
                        validator: v.all([v.password(), v.maxLength(128)]),
                      ),
                      const SizedBox(height: 8),
                      PasswordStrengthChecklist(controller: _newPwCtrl),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _confirmPwCtrl,
                        focusNode: _confirmPwFocusNode,
                        obscureText: _obscureConfirm,
                        decoration: InputDecoration(
                          labelText: 'one more time',
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureConfirm
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                            tooltip: _obscureConfirm
                                ? 'Show password'
                                : 'Hide password',
                            onPressed: () => setState(
                              () => _obscureConfirm = !_obscureConfirm,
                            ),
                          ),
                        ),
                        textInputAction: TextInputAction.done,
                        onFieldSubmitted: (_) => _saving ? null : _save(),
                        validator: (v) => v != _newPwCtrl.text
                            ? 'Passwords do not match'
                            : null,
                      ),
                      const SizedBox(height: 24),
                      FilledButton(
                        onPressed: _saving ? null : _save,
                        child: _saving
                            ? const SizedBox(
                                width: 16,
                                height: 16,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text('save & continue'),
                      ),
                    ],
                  ),
                ),
              ),
            ),
          ),
        ),
      ),
    );
  }
}
