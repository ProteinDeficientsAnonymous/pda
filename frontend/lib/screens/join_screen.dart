import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/join_request_provider.dart';
import 'package:pda/widgets/phone_form_field.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/app_scaffold.dart';

class JoinScreen extends ConsumerStatefulWidget {
  const JoinScreen({super.key});

  @override
  ConsumerState<JoinScreen> createState() => _JoinScreenState();
}

class _JoinScreenState extends ConsumerState<JoinScreen> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameController = TextEditingController();
  final _emailController = TextEditingController();
  final _pronounsController = TextEditingController();
  final _howController = TextEditingController();
  final _whyController = TextEditingController();
  String _phoneNumber = '';

  @override
  void dispose() {
    _displayNameController.dispose();
    _emailController.dispose();
    _pronounsController.dispose();
    _howController.dispose();
    _whyController.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_phoneNumber.isEmpty) return;
    await ref
        .read(joinRequestProvider.notifier)
        .submit(
          displayName: _displayNameController.text.trim(),
          phoneNumber: _phoneNumber,
          email: _emailController.text.trim(),
          pronouns: _pronounsController.text.trim(),
          howTheyHeard: _howController.text.trim(),
          whyJoin: _whyController.text.trim(),
        );
    final state = ref.read(joinRequestProvider);
    if (state.hasError) return;
    if (mounted) context.go('/join/success');
  }

  @override
  Widget build(BuildContext context) {
    final state = ref.watch(joinRequestProvider);
    final isLoading = state.isLoading;

    return AppScaffold(
      child: SingleChildScrollView(
        child: Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 600),
            child: Padding(
              padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 48),
              child: Form(
                key: _formKey,
                child: FocusTraversalGroup(
                  policy: OrderedTraversalPolicy(),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Request to join PDA',
                        style: Theme.of(context).textTheme.headlineMedium,
                      ),
                      const SizedBox(height: 8),
                      Text(
                        'We review all requests. You\'ll hear from us once a '
                        'vetting member has reviewed your submission.',
                        style: TextStyle(color: Colors.grey[700], fontSize: 15),
                      ),
                      const SizedBox(height: 32),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(1),
                        child: TextFormField(
                          controller: _displayNameController,
                          decoration: const InputDecoration(
                            labelText: 'Display name *',
                            hintText: 'e.g. Alex R',
                            helperText:
                                'Letters and spaces only; at least first name + '
                                'last initial',
                            border: OutlineInputBorder(),
                          ),
                          validator: v.displayName(),
                        ),
                      ),
                      const SizedBox(height: 16),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(2),
                        child: PhoneFormField(
                          labelText: 'Phone number *',
                          helperText:
                              'Use the phone number you use (or will use) '
                              'to connect with the PDA community.',
                          onChanged: (number) => _phoneNumber = number,
                        ),
                      ),
                      const SizedBox(height: 16),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(3),
                        child: TextFormField(
                          controller: _emailController,
                          decoration: const InputDecoration(
                            labelText: 'Email (optional)',
                            border: OutlineInputBorder(),
                          ),
                          keyboardType: TextInputType.emailAddress,
                          validator: v.optionalEmail(),
                        ),
                      ),
                      const SizedBox(height: 16),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(4),
                        child: TextFormField(
                          controller: _pronounsController,
                          decoration: const InputDecoration(
                            labelText: 'Pronouns (optional)',
                            border: OutlineInputBorder(),
                          ),
                          validator: v.maxLength(100),
                        ),
                      ),
                      const SizedBox(height: 16),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(5),
                        child: TextFormField(
                          controller: _howController,
                          decoration: const InputDecoration(
                            labelText: 'How did you hear about us? (optional)',
                            border: OutlineInputBorder(),
                          ),
                          validator: v.maxLength(500),
                        ),
                      ),
                      const SizedBox(height: 16),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(6),
                        child: TextFormField(
                          controller: _whyController,
                          decoration: const InputDecoration(
                            labelText: 'Why do you want to join? *',
                            border: OutlineInputBorder(),
                            alignLabelWithHint: true,
                          ),
                          maxLines: 5,
                          validator: v.all([
                            v.required(),
                            v.minLength(
                              20,
                              'Please tell us a bit more (min 20 characters)',
                            ),
                            v.maxLength(2000),
                          ]),
                        ),
                      ),
                      if (state.hasError) ...[
                        const SizedBox(height: 16),
                        Text(
                          state.error is ApiError
                              ? (state.error! as ApiError).message
                              : 'Something went wrong. Please try again.',
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ],
                      const SizedBox(height: 24),
                      FocusTraversalOrder(
                        order: const NumericFocusOrder(7),
                        child: SizedBox(
                          width: double.infinity,
                          child: FilledButton(
                            onPressed: isLoading ? null : _submit,
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
                                      'Submit request',
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
