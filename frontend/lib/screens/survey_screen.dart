import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/survey_provider.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/config/constants.dart';

class SurveyScreen extends ConsumerWidget {
  final String slug;

  const SurveyScreen({super.key, required this.slug});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final surveyAsync = ref.watch(surveyBySlugProvider(slug));

    return AppScaffold(
      maxWidth: 600,
      child: surveyAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error:
            (e, _) => const Center(
              child: Text('couldn\'t find that survey — it may be closed'),
            ),
        data: (survey) => _SurveyForm(survey: survey),
      ),
    );
  }
}

class _SurveyForm extends ConsumerStatefulWidget {
  final Survey survey;

  const _SurveyForm({required this.survey});

  @override
  ConsumerState<_SurveyForm> createState() => _SurveyFormState();
}

class _SurveyFormState extends ConsumerState<_SurveyForm> {
  final _formKey = GlobalKey<FormState>();
  final Map<String, String> _answers = {};
  bool _submitting = false;
  bool _submitted = false;

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    _formKey.currentState!.save();

    setState(() => _submitting = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.post(
        '/api/community/surveys/view/${widget.survey.slug}/respond/',
        data: {'answers': _answers},
      );
      setState(() => _submitted = true);
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, 'couldn\'t submit — try again');
      }
    } finally {
      if (mounted) setState(() => _submitting = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);

    if (_submitted) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(
                Icons.check_circle_outline_rounded,
                size: 56,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(height: 16),
              Text(
                'thanks for your feedback! 🌱',
                style: theme.textTheme.headlineSmall,
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      );
    }

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(widget.survey.title, style: theme.textTheme.headlineSmall),
                if (widget.survey.description.isNotEmpty) ...[
                  const SizedBox(height: 8),
                  Text(
                    widget.survey.description,
                    style: TextStyle(
                      color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                    ),
                  ),
                ],
                const SizedBox(height: 24),
                ...widget.survey.questions.map(
                  (q) => Padding(
                    padding: const EdgeInsets.only(bottom: 20),
                    child: _QuestionField(
                      question: q,
                      onSaved: (value) {
                        if (value != null && value.isNotEmpty) {
                          _answers[q.id] = value;
                        }
                      },
                    ),
                  ),
                ),
                const SizedBox(height: 8),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton(
                    onPressed: _submitting ? null : _submit,
                    child:
                        _submitting
                            ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(strokeWidth: 2),
                            )
                            : const Text('submit'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    );
  }
}

class _QuestionField extends StatelessWidget {
  final SurveyQuestion question;
  final FormFieldSetter<String> onSaved;

  const _QuestionField({required this.question, required this.onSaved});

  String? _validate(String? value) {
    if (question.required && (value == null || value.trim().isEmpty)) {
      return 'Required';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final label = '${question.label}${question.required ? ' *' : ''}';

    return switch (question.fieldType) {
      FieldType.textarea => TextFormField(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
        maxLines: 4,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.select => _RadioField(
        label: label,
        options: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.multiselect => _CheckboxField(
        label: label,
        options: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.dropdown => _DropdownField(
        label: label,
        options: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.number => TextFormField(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
        keyboardType: TextInputType.number,
        validator: (v) {
          final base = _validate(v);
          if (base != null) return base;
          if (v != null && v.isNotEmpty) {
            if (double.tryParse(v) == null) return 'Must be a number';
          }
          return null;
        },
        onSaved: onSaved,
      ),
      FieldType.yesNo => _RadioField(
        label: label,
        options: const ['yes', 'no'],
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.rating => _RatingField(
        label: label,
        ratingLabels: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      _ => TextFormField(
        decoration: InputDecoration(
          labelText: label,
          border: const OutlineInputBorder(),
        ),
        validator: _validate,
        onSaved: onSaved,
      ),
    };
  }
}

class _RadioField extends FormField<String> {
  _RadioField({
    required String label,
    required List<String> options,
    required FormFieldValidator<String> validator,
    required FormFieldSetter<String> onSaved,
  }) : super(
         initialValue: '',
         validator: validator,
         onSaved: onSaved,
         builder: (state) {
           return Column(
             crossAxisAlignment: CrossAxisAlignment.start,
             children: [
               Text(label),
               RadioGroup<String>(
                 groupValue: state.value,
                 onChanged: (v) => state.didChange(v),
                 child: Column(
                   children:
                       options
                           .map(
                             (option) => RadioListTile<String>(
                               title: Text(option),
                               value: option,
                               dense: true,
                               contentPadding: EdgeInsets.zero,
                             ),
                           )
                           .toList(),
                 ),
               ),
               if (state.hasError)
                 Padding(
                   padding: const EdgeInsets.only(left: 12, top: 4),
                   child: Text(
                     state.errorText!,
                     style: TextStyle(
                       color: Theme.of(state.context).colorScheme.error,
                       fontSize: 12,
                     ),
                   ),
                 ),
             ],
           );
         },
       );
}

class _CheckboxField extends FormField<String> {
  _CheckboxField({
    required String label,
    required List<String> options,
    required FormFieldValidator<String> validator,
    required FormFieldSetter<String> onSaved,
  }) : super(
         initialValue: '',
         validator: validator,
         onSaved: onSaved,
         builder: (state) {
           final selected =
               (state.value ?? '')
                   .split(',')
                   .map((s) => s.trim())
                   .where((s) => s.isNotEmpty)
                   .toSet();
           return Column(
             crossAxisAlignment: CrossAxisAlignment.start,
             children: [
               Text(label),
               ...options.map(
                 (option) => CheckboxListTile(
                   title: Text(option),
                   value: selected.contains(option),
                   onChanged: (checked) {
                     final next = Set<String>.from(selected);
                     if (checked == true) {
                       next.add(option);
                     } else {
                       next.remove(option);
                     }
                     state.didChange(next.join(','));
                   },
                   dense: true,
                   contentPadding: EdgeInsets.zero,
                 ),
               ),
               if (state.hasError)
                 Padding(
                   padding: const EdgeInsets.only(left: 12, top: 4),
                   child: Text(
                     state.errorText!,
                     style: TextStyle(
                       color: Theme.of(state.context).colorScheme.error,
                       fontSize: 12,
                     ),
                   ),
                 ),
             ],
           );
         },
       );
}

class _DropdownField extends StatelessWidget {
  final String label;
  final List<String> options;
  final FormFieldValidator<String> validator;
  final FormFieldSetter<String> onSaved;

  const _DropdownField({
    required this.label,
    required this.options,
    required this.validator,
    required this.onSaved,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      decoration: InputDecoration(
        labelText: label,
        border: const OutlineInputBorder(),
      ),
      items:
          options
              .map((o) => DropdownMenuItem(value: o, child: Text(o)))
              .toList(),
      validator: validator,
      onSaved: onSaved,
      onChanged: (_) {},
    );
  }
}

class _RatingField extends FormField<String> {
  _RatingField({
    required String label,
    List<String> ratingLabels = const [],
    required FormFieldValidator<String> validator,
    required FormFieldSetter<String> onSaved,
  }) : super(
         initialValue: '',
         validator: validator,
         onSaved: onSaved,
         builder: (state) {
           final current = int.tryParse(state.value ?? '') ?? 0;
           final theme = Theme.of(state.context);
           // ratingLabels[0] = label for 1 star, [4] = label for 5 stars
           String? labelFor(int star) {
             final idx = star - 1;
             if (idx < ratingLabels.length && ratingLabels[idx].isNotEmpty) {
               return ratingLabels[idx];
             }
             return null;
           }

           final currentLabel = current > 0 ? labelFor(current) : null;

           return Column(
             crossAxisAlignment: CrossAxisAlignment.start,
             children: [
               Text(label),
               const SizedBox(height: 8),
               Row(
                 children: [
                   // Low label
                   if (ratingLabels.isNotEmpty) ...[
                     Text(
                       labelFor(1) ?? '',
                       style: TextStyle(
                         fontSize: 11,
                         color: theme.colorScheme.onSurface.withValues(
                           alpha: 0.4,
                         ),
                       ),
                     ),
                     const SizedBox(width: 4),
                   ],
                   ...List.generate(5, (i) {
                     final star = i + 1;
                     return IconButton(
                       icon: Icon(
                         star <= current
                             ? Icons.star_rounded
                             : Icons.star_outline_rounded,
                         color:
                             star <= current
                                 ? theme.colorScheme.primary
                                 : theme.colorScheme.onSurface.withValues(
                                   alpha: 0.3,
                                 ),
                         size: 32,
                       ),
                       onPressed: () => state.didChange('$star'),
                       tooltip: labelFor(star) ?? '$star',
                     );
                   }),
                   // High label
                   if (ratingLabels.length >= 5) ...[
                     const SizedBox(width: 4),
                     Text(
                       labelFor(5) ?? '',
                       style: TextStyle(
                         fontSize: 11,
                         color: theme.colorScheme.onSurface.withValues(
                           alpha: 0.4,
                         ),
                       ),
                     ),
                   ],
                 ],
               ),
               if (currentLabel != null)
                 Padding(
                   padding: const EdgeInsets.only(top: 4),
                   child: Text(
                     currentLabel,
                     style: TextStyle(
                       fontSize: 13,
                       color: theme.colorScheme.primary,
                       fontWeight: FontWeight.w500,
                     ),
                   ),
                 ),
               if (state.hasError)
                 Padding(
                   padding: const EdgeInsets.only(left: 12, top: 4),
                   child: Text(
                     state.errorText!,
                     style: TextStyle(
                       color: theme.colorScheme.error,
                       fontSize: 12,
                     ),
                   ),
                 ),
             ],
           );
         },
       );
}
