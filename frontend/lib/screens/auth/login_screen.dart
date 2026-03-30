import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/phone_form_field.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  final _passwordFocusNode = FocusNode();
  String _phoneNumber = '';
  bool _obscurePassword = true;

  @override
  void dispose() {
    _passwordController.dispose();
    _passwordFocusNode.dispose();
    super.dispose();
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    if (_phoneNumber.isEmpty) return;
    await ref
        .read(authProvider.notifier)
        .login(_phoneNumber, _passwordController.text);
    final authState = ref.read(authProvider);
    if (authState.hasError) return;
    if (mounted) {
      final redirect =
          GoRouterState.of(context).uri.queryParameters['redirect'];
      context.go(redirect ?? '/calendar');
    }
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(authProvider);
    final isLoading = state.isLoading;

    return AppScaffold(
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 440),
          child: Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 48),
            child: Form(
              key: _formKey,
              child: AutofillGroup(
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
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(1),
                        child: PhoneFormField(
                          onChanged: (number) => _phoneNumber = number,
                          textInputAction: TextInputAction.done,
                          onFieldSubmitted:
                              (_) => _passwordFocusNode.requestFocus(),
                        ),
                      ),
                      const SizedBox(height: 16),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(2),
                        child: TextFormField(
                          controller: _passwordController,
                          focusNode: _passwordFocusNode,
                          autofillHints: const [AutofillHints.password],
                          decoration: InputDecoration(
                            labelText: 'Password',
                            border: const OutlineInputBorder(),
                            suffixIcon: IconButton(
                              icon: Icon(
                                _obscurePassword
                                    ? Icons.visibility_off
                                    : Icons.visibility,
                              ),
                              tooltip:
                                  _obscurePassword
                                      ? 'Show password'
                                      : 'Hide password',
                              onPressed:
                                  () => setState(
                                    () => _obscurePassword = !_obscurePassword,
                                  ),
                            ),
                          ),
                          obscureText: _obscurePassword,
                          textInputAction: TextInputAction.done,
                          onFieldSubmitted: (_) => isLoading ? null : _login(),
                          validator:
                              (v) => v == null || v.isEmpty ? 'Required' : null,
                        ),
                      ),
                      if (state.hasError) ...[
                        const SizedBox(height: 16),
                        Text(
                          state.error is ApiError
                              ? (state.error! as ApiError).message
                              : 'something went wrong — try again',
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(3),
                        child: SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: isLoading ? null : _login,
                            style: FilledButton.styleFrom(
                              padding: const EdgeInsets.symmetric(vertical: 16),
                            ),
                            child:
                                isLoading
                                    ? const SizedBox(
                                      height: 20,
                                      width: 20,
                                      child: CircularProgressIndicator(
                                        strokeWidth: 2,
                                      ),
                                    )
                                    : const Text(
                                      'log in',
                                      style: TextStyle(fontSize: 16),
                                    ),
                          ),
                        ),
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
