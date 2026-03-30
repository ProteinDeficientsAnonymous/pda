import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/widgets/app_scaffold.dart';

class NewPasswordScreen extends ConsumerStatefulWidget {
  const NewPasswordScreen({super.key});

  @override
  ConsumerState<NewPasswordScreen> createState() => _NewPasswordScreenState();
}

class _NewPasswordScreenState extends ConsumerState<NewPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _newPwCtrl = TextEditingController();
  final _confirmPwCtrl = TextEditingController();
  final _confirmPwFocusNode = FocusNode();
  bool _saving = false;
  bool _obscureNew = true;
  bool _obscureConfirm = true;

  @override
  void dispose() {
    _newPwCtrl.dispose();
    _confirmPwCtrl.dispose();
    _confirmPwFocusNode.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _saving = true);
    try {
      await ref
          .read(authProvider.notifier)
          .completeOnboarding(newPassword: _newPwCtrl.text);
      // Router redirect will navigate to /calendar once needsOnboarding becomes false.
    } on DioException catch (e) {
      if (!mounted) return;
      final detail =
          (e.response?.data as Map?)?['detail'] ?? 'couldn\'t save — try again';
      ScaffoldMessenger.of(
        context,
      ).showSnackBar(SnackBar(content: Text(detail.toString())));
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
                        'set a new password',
                        style: Theme.of(context).textTheme.headlineSmall,
                      ),
                      const SizedBox(height: 8),
                      const Text(
                        'your password was reset — choose a new one to continue',
                        style: TextStyle(color: Colors.grey),
                      ),
                      const SizedBox(height: 24),
                      TextFormField(
                        controller: _newPwCtrl,
                        obscureText: _obscureNew,
                        decoration: InputDecoration(
                          labelText: 'New password',
                          border: const OutlineInputBorder(),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureNew
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                            tooltip:
                                _obscureNew ? 'Show password' : 'Hide password',
                            onPressed:
                                () =>
                                    setState(() => _obscureNew = !_obscureNew),
                          ),
                        ),
                        textInputAction: TextInputAction.next,
                        onFieldSubmitted:
                            (_) => _confirmPwFocusNode.requestFocus(),
                        validator:
                            (v) =>
                                (v == null || v.length < 8)
                                    ? 'At least 8 characters'
                                    : null,
                      ),
                      const SizedBox(height: 12),
                      TextFormField(
                        controller: _confirmPwCtrl,
                        focusNode: _confirmPwFocusNode,
                        obscureText: _obscureConfirm,
                        decoration: InputDecoration(
                          labelText: 'Confirm new password',
                          border: const OutlineInputBorder(),
                          suffixIcon: IconButton(
                            icon: Icon(
                              _obscureConfirm
                                  ? Icons.visibility_off
                                  : Icons.visibility,
                            ),
                            tooltip:
                                _obscureConfirm
                                    ? 'Show password'
                                    : 'Hide password',
                            onPressed:
                                () => setState(
                                  () => _obscureConfirm = !_obscureConfirm,
                                ),
                          ),
                        ),
                        textInputAction: TextInputAction.done,
                        onFieldSubmitted: (_) => _saving ? null : _save(),
                        validator:
                            (v) =>
                                v != _newPwCtrl.text
                                    ? 'Passwords do not match'
                                    : null,
                      ),
                      const SizedBox(height: 24),
                      FilledButton(
                        onPressed: _saving ? null : _save,
                        child:
                            _saving
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
