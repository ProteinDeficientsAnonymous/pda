import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/join_form_question.dart';
import 'package:pda/providers/join_form_provider.dart';
import 'package:pda/providers/join_request_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/phone_form_field.dart';
import 'package:pda/config/constants.dart';

class JoinScreen extends ConsumerStatefulWidget {
  const JoinScreen({super.key});

  @override
  ConsumerState<JoinScreen> createState() => _JoinScreenState();
}

class _JoinScreenState extends ConsumerState<JoinScreen> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameController = TextEditingController();
  String _phoneNumber = '';

  final _textControllers = <String, TextEditingController>{};
  final _selectValues = <String, String?>{};

  @override
  void dispose() {
    _displayNameController.dispose();
    for (final c in _textControllers.values) {
      c.dispose();
    }
    super.dispose();
  }

  TextEditingController _controllerFor(String questionId) {
    return _textControllers.putIfAbsent(
      questionId,
      () => TextEditingController(),
    );
  }

  Future<void> _submit(List<JoinFormQuestion> questions) async {
    if (!_formKey.currentState!.validate()) return;
    if (_phoneNumber.isEmpty) return;

    final answers = <String, String>{};
    for (final q in questions) {
      if (q.fieldType == FieldType.select) {
        final val = _selectValues[q.id];
        if (val != null && val.isNotEmpty) answers[q.id] = val;
      } else {
        final val = _textControllers[q.id]?.text.trim() ?? '';
        if (val.isNotEmpty) answers[q.id] = val;
      }
    }

    await ref
        .read(joinRequestProvider.notifier)
        .submit(
          displayName: _displayNameController.text.trim(),
          phoneNumber: _phoneNumber,
          answers: answers,
        );
    final state = ref.read(joinRequestProvider);
    if (state.hasError) return;
    if (mounted) context.go('/join/success');
  }

  @override
  Widget build(BuildContext context) {
    final submitState = ref.watch(joinRequestProvider);
    final isLoading = submitState.isLoading;
    final questionsAsync = ref.watch(joinFormProvider);

    return AppScaffold(
      maxWidth: 600,
      child: questionsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (e, _) => const Center(
              child: Text('couldn\'t load the form — try refreshing'),
            ),
        data:
            (questions) =>
                _buildForm(context, questions, isLoading, submitState),
      ),
    );
  }

  Widget _buildForm(
    BuildContext context,
    List<JoinFormQuestion> questions,
    bool isLoading,
    AsyncValue<void> submitState,
  ) {
    var focusOrder = 3; // 1=name, 2=phone, then dynamic

    return SingleChildScrollView(
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
                      'request to join PDA',
                      style: Theme.of(context).textTheme.headlineMedium,
                    ),
                    const SizedBox(height: 8),
                    Text(
                      'we review all requests — you\'ll hear from us once a '
                      'vetting member has had a look',
                      style: TextStyle(color: Colors.grey[700], fontSize: 15),
                    ),
                    const SizedBox(height: 32),
                    FocusTraversalOrder(
                      order: const NumericFocusOrder(1),
                      child: TextFormField(
                        controller: _displayNameController,
                        decoration: const InputDecoration(
                          labelText: 'display name *',
                          hintText: 'e.g. Alex R',
                          helperText:
                              'letters and spaces only; at least first name + '
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
                        labelText: 'phone number *',
                        helperText:
                            'Use the phone number you use (or will use) '
                            'to connect with the PDA community.',
                        onChanged: (number) => _phoneNumber = number,
                      ),
                    ),
                    for (final q in questions) ...[
                      const SizedBox(height: 16),
                      _buildQuestionField(q, focusOrder++),
                    ],
                    if (submitState.hasError) ...[
                      const SizedBox(height: 16),
                      Text(
                        submitState.error is ApiError
                            ? (submitState.error! as ApiError).message
                            : 'something went wrong — try again',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.error,
                        ),
                      ),
                    ],
                    const SizedBox(height: 24),
                    FocusTraversalOrder(
                      order: NumericFocusOrder(focusOrder.toDouble()),
                      child: SizedBox(
                        width: double.infinity,
                        child: FilledButton(
                          onPressed:
                              isLoading ? null : () => _submit(questions),
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
                                    'submit request',
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
    );
  }

  Widget _buildQuestionField(JoinFormQuestion q, int order) {
    final label = '${q.label}${q.required ? ' *' : ''}';

    if (q.fieldType == FieldType.select) {
      return FocusTraversalOrder(
        order: NumericFocusOrder(order.toDouble()),
        child: DropdownButtonFormField<String>(
          initialValue: _selectValues[q.id],
          decoration: InputDecoration(
            labelText: label,
            border: const OutlineInputBorder(),
          ),
          items:
              q.options
                  .map((opt) => DropdownMenuItem(value: opt, child: Text(opt)))
                  .toList(),
          onChanged: (val) => setState(() => _selectValues[q.id] = val),
          validator:
              q.required
                  ? (val) => (val == null || val.isEmpty) ? 'Required' : null
                  : null,
        ),
      );
    }

    return FocusTraversalOrder(
      order: NumericFocusOrder(order.toDouble()),
      child: TextFormField(
        controller: _controllerFor(q.id),
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
        maxLines: q.label.toLowerCase().contains('why') ? 5 : 1,
        validator:
            q.required
                ? v.all([v.required(), v.maxLength(2000)])
                : v.maxLength(2000),
      ),
    );
  }
}
