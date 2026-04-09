import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/phone_form_field.dart';

final _log = Logger('LoginScreen');

enum _LoginStep { phone, password, pending, unknown }

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _phoneFormKey = GlobalKey<FormState>();
  final _passwordFormKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  final _passwordFocusNode = FocusNode();
  String _phoneNumber = '';
  bool _obscurePassword = true;
  bool _loading = false;
  String? _error;
  _LoginStep _step = _LoginStep.phone;

  @override
  void dispose() {
    _passwordController.dispose();
    _passwordFocusNode.dispose();
    super.dispose();
  }

  Future<void> _checkPhone() async {
    if (!_phoneFormKey.currentState!.validate()) return;
    if (_phoneNumber.isEmpty) return;
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
            _step = _LoginStep.password;
          case 'pending':
            _step = _LoginStep.pending;
          default:
            _step = _LoginStep.unknown;
        }
      });
      if (_step == _LoginStep.password) {
        _passwordFocusNode.requestFocus();
      }
    } catch (e, st) {
      _log.warning('phone check failed', e, st);
      if (mounted) {
        setState(() {
          _error = ApiError.from(e).message;
          _loading = false;
        });
      }
    }
  }

  Future<void> _requestLoginLink() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.post(
        '/api/community/request-login-link/',
        data: {'phone_number': _phoneNumber},
      );
      final detail =
          (resp.data as Map<String, dynamic>)['detail'] as String? ??
          'if you\'ve been invited, an admin will be in touch';
      if (mounted) {
        setState(() => _loading = false);
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(SnackBar(content: Text(detail)));
      }
    } catch (e, st) {
      _log.warning('request login link failed', e, st);
      if (mounted) {
        setState(() {
          _error = ApiError.from(e).message;
          _loading = false;
        });
      }
    }
  }

  Future<void> _login() async {
    if (!_passwordFormKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .login(_phoneNumber, _passwordController.text);
      final authState = ref.read(authProvider);
      if (authState.hasError) {
        if (mounted) {
          setState(() {
            _error = authState.error is ApiError
                ? (authState.error! as ApiError).message
                : 'something went wrong — try again';
            _loading = false;
          });
        }
        return;
      }
      TextInput.finishAutofillContext();
      _log.info('login succeeded');
      if (mounted) {
        final redirect = GoRouterState.of(
          context,
        ).uri.queryParameters['redirect'];
        context.go(redirect ?? '/calendar');
      }
    } catch (e, st) {
      _log.warning('login failed', e, st);
      if (mounted) {
        setState(() {
          _error = ApiError.from(e).message;
          _loading = false;
        });
      }
    }
  }

  void _resetToPhone() {
    setState(() {
      _step = _LoginStep.phone;
      _error = null;
      _passwordController.clear();
    });
  }

  @override
  Widget build(BuildContext context) {
    final invited =
        GoRouterState.of(context).uri.queryParameters['invited'] == 'true';
    return AppScaffold(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 48),
            child: switch (_step) {
              _LoginStep.phone => _PhoneStep(
                formKey: _phoneFormKey,
                onChanged: (v) => _phoneNumber = v,
                onSubmit: _checkPhone,
                loading: _loading,
                error: _error,
                invited: invited,
              ),
              _LoginStep.password => _PasswordStep(
                formKey: _passwordFormKey,
                controller: _passwordController,
                focusNode: _passwordFocusNode,
                obscure: _obscurePassword,
                onToggleObscure: () =>
                    setState(() => _obscurePassword = !_obscurePassword),
                onSubmit: _login,
                onBack: _resetToPhone,
                onRequestLoginLink: _requestLoginLink,
                loading: _loading,
                error: _error,
              ),
              _LoginStep.pending => _PendingStep(onBack: _resetToPhone),
              _LoginStep.unknown => _UnknownStep(onBack: _resetToPhone),
            },
          ),
        ),
      ),
    );
  }
}

class _PhoneStep extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final ValueChanged<String> onChanged;
  final VoidCallback onSubmit;
  final bool loading;
  final String? error;
  final bool invited;

  const _PhoneStep({
    required this.formKey,
    required this.onChanged,
    required this.onSubmit,
    required this.loading,
    required this.error,
    this.invited = false,
  });

  @override
  Widget build(BuildContext context) {
    return Form(
      key: formKey,
      child: FocusTraversalGroup(
        policy: OrderedTraversalPolicy(),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'member login',
              style: Theme.of(context).textTheme.headlineMedium,
            ),
            const SizedBox(height: 8),
            Text(
              'this area is for approved PDA members only',
              style: TextStyle(color: Colors.grey[700]),
            ),
            const SizedBox(height: 32),
            if (invited) ...[
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: Colors.green.shade50,
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: Colors.green.shade200),
                ),
                child: const Text(
                  "you've already been invited! enter your phone number to log in",
                ),
              ),
              const SizedBox(height: 16),
            ],
            FocusTraversalOrder(
              order: const NumericFocusOrder(1),
              child: PhoneFormField(
                onChanged: onChanged,
                textInputAction: TextInputAction.done,
                onFieldSubmitted: (_) => loading ? null : onSubmit(),
              ),
            ),
            if (error != null) ...[
              const SizedBox(height: 16),
              Text(
                error!,
                style: TextStyle(color: Theme.of(context).colorScheme.error),
              ),
            ],
            const SizedBox(height: 24),
            FocusTraversalOrder(
              order: const NumericFocusOrder(2),
              child: SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: loading ? null : onSubmit,
                  style: FilledButton.styleFrom(
                    padding: const EdgeInsets.symmetric(vertical: 16),
                  ),
                  child: loading
                      ? const SizedBox(
                          height: 20,
                          width: 20,
                          child: CircularProgressIndicator(strokeWidth: 2),
                        )
                      : const Text('continue', style: TextStyle(fontSize: 16)),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _PasswordStep extends StatelessWidget {
  final GlobalKey<FormState> formKey;
  final TextEditingController controller;
  final FocusNode focusNode;
  final bool obscure;
  final VoidCallback onToggleObscure;
  final VoidCallback onSubmit;
  final VoidCallback onBack;
  final VoidCallback onRequestLoginLink;
  final bool loading;
  final String? error;

  const _PasswordStep({
    required this.formKey,
    required this.controller,
    required this.focusNode,
    required this.obscure,
    required this.onToggleObscure,
    required this.onSubmit,
    required this.onBack,
    required this.onRequestLoginLink,
    required this.loading,
    required this.error,
  });

  @override
  Widget build(BuildContext context) {
    return Form(
      key: formKey,
      child: AutofillGroup(
        child: FocusTraversalGroup(
          policy: OrderedTraversalPolicy(),
          child: SingleChildScrollView(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'welcome back!',
                  style: Theme.of(context).textTheme.headlineMedium,
                ),
                const SizedBox(height: 8),
                Text(
                  'pop in your password to get in',
                  style: TextStyle(color: Colors.grey[700]),
                ),
                const SizedBox(height: 32),
                FocusTraversalOrder(
                  order: const NumericFocusOrder(1),
                  child: TextFormField(
                    controller: controller,
                    focusNode: focusNode,
                    autofillHints: const [AutofillHints.password],
                    decoration: InputDecoration(
                      labelText: 'Password',
                      border: const OutlineInputBorder(),
                      suffixIcon: IconButton(
                        icon: Icon(
                          obscure ? Icons.visibility_off : Icons.visibility,
                        ),
                        tooltip: obscure ? 'Show password' : 'Hide password',
                        onPressed: onToggleObscure,
                      ),
                    ),
                    obscureText: obscure,
                    enableInteractiveSelection: true,
                    enableSuggestions: false,
                    autocorrect: false,
                    textInputAction: TextInputAction.done,
                    onFieldSubmitted: (_) => loading ? null : onSubmit(),
                    validator: (v) =>
                        v == null || v.isEmpty ? 'Required' : null,
                  ),
                ),
                if (error != null) ...[
                  const SizedBox(height: 16),
                  Text(
                    error!,
                    style: TextStyle(
                      color: Theme.of(context).colorScheme.error,
                    ),
                  ),
                ],
                const SizedBox(height: 24),
                FocusTraversalOrder(
                  order: const NumericFocusOrder(2),
                  child: SizedBox(
                    width: double.infinity,
                    child: FilledButton(
                      onPressed: loading ? null : onSubmit,
                      style: FilledButton.styleFrom(
                        padding: const EdgeInsets.symmetric(vertical: 16),
                      ),
                      child: loading
                          ? const SizedBox(
                              height: 20,
                              width: 20,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                          : const Text(
                              'log in',
                              style: TextStyle(fontSize: 16),
                            ),
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                TextButton(
                  onPressed: loading ? null : onRequestLoginLink,
                  child: const Text('lost your login link? request a new one'),
                ),
                TextButton(
                  onPressed: onBack,
                  child: const Text('← use a different number'),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _PendingStep extends StatelessWidget {
  final VoidCallback onBack;

  const _PendingStep({required this.onBack});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'your request is in review ⏳',
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 16),
        Text(
          "hang tight — we'll be in touch soon",
          style: TextStyle(color: Colors.grey[700]),
        ),
        const SizedBox(height: 24),
        TextButton(
          onPressed: onBack,
          child: const Text('← use a different number'),
        ),
      ],
    );
  }
}

class _UnknownStep extends StatelessWidget {
  final VoidCallback onBack;

  const _UnknownStep({required this.onBack});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          "we don't recognise that number",
          style: Theme.of(context).textTheme.headlineMedium,
        ),
        const SizedBox(height: 16),
        Text(
          "not a member yet? request to join and we'll sort you out",
          style: TextStyle(color: Colors.grey[700]),
        ),
        const SizedBox(height: 24),
        SizedBox(
          width: double.infinity,
          child: FilledButton(
            onPressed: () => context.go('/join'),
            style: FilledButton.styleFrom(
              padding: const EdgeInsets.symmetric(vertical: 16),
            ),
            child: const Text(
              'request to join',
              style: TextStyle(fontSize: 16),
            ),
          ),
        ),
        const SizedBox(height: 16),
        TextButton(
          onPressed: onBack,
          child: const Text('← try a different number'),
        ),
      ],
    );
  }
}
