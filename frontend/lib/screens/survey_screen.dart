import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/poll_provider.dart';
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
      ref.invalidate(surveyBySlugProvider(widget.survey.slug));
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

    final isUpdate = widget.survey.myResponseId != null;
    final isFinalized = widget.survey.pollResult != null;

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 560),
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
              if (isFinalized) ...[
                const SizedBox(height: 16),
                _PollResultBanner(pollResult: widget.survey.pollResult!),
              ],
              const SizedBox(height: 24),
              Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    ...widget.survey.questions.map(
                      (q) => Padding(
                        padding: const EdgeInsets.only(bottom: 20),
                        child: _QuestionField(
                          question: q,
                          survey: widget.survey,
                          isFinalized: isFinalized,
                          onSaved: (value) {
                            if (value != null && value.isNotEmpty) {
                              _answers[q.id] = value;
                            }
                          },
                        ),
                      ),
                    ),
                    if (!isFinalized) ...[
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
                                    child: CircularProgressIndicator(
                                      strokeWidth: 2,
                                    ),
                                  )
                                  : Text(isUpdate ? 'update vote' : 'submit'),
                        ),
                      ),
                    ],
                  ],
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _PollResultBanner extends StatelessWidget {
  final PollResult pollResult;

  const _PollResultBanner({required this.pollResult});

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final dt = pollResult.winningDatetime.toLocal();
    final formatted = DateFormat('EEEE, MMMM d · h:mm a').format(dt);
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: theme.colorScheme.primaryContainer,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Row(
        children: [
          Icon(
            Icons.check_circle_rounded,
            color: theme.colorScheme.primary,
            size: 20,
          ),
          const SizedBox(width: 12),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'time chosen!',
                  style: theme.textTheme.labelMedium?.copyWith(
                    color: theme.colorScheme.onPrimaryContainer,
                    fontWeight: FontWeight.w600,
                  ),
                ),
                Text(
                  formatted.toLowerCase(),
                  style: theme.textTheme.bodyMedium?.copyWith(
                    color: theme.colorScheme.onPrimaryContainer,
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _QuestionField extends StatelessWidget {
  final SurveyQuestion question;
  final Survey survey;
  final bool isFinalized;
  final FormFieldSetter<String> onSaved;

  const _QuestionField({
    required this.question,
    required this.survey,
    required this.isFinalized,
    required this.onSaved,
  });

  String? _validate(String? value) {
    if (question.required && (value == null || value.trim().isEmpty)) {
      return 'Required';
    }
    return null;
  }

  @override
  Widget build(BuildContext context) {
    final label = '${question.label}${question.required ? ' *' : ''}';

    if (question.fieldType == FieldType.datetimePoll) {
      return _DatetimePollField(
        question: question,
        survey: survey,
        isFinalized: isFinalized,
        validator: _validate,
        onSaved: onSaved,
      );
    }

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

/// Formats an ISO 8601 datetime string for display in a poll option.
String _formatPollOption(String iso) {
  try {
    final dt = DateTime.parse(iso).toLocal();
    return DateFormat('EEE, MMM d · h:mm a').format(dt).toLowerCase();
  } catch (_) {
    return iso;
  }
}

class _DatetimePollField extends ConsumerStatefulWidget {
  final SurveyQuestion question;
  final Survey survey;
  final bool isFinalized;
  final FormFieldValidator<String> validator;
  final FormFieldSetter<String> onSaved;

  const _DatetimePollField({
    required this.question,
    required this.survey,
    required this.isFinalized,
    required this.validator,
    required this.onSaved,
  });

  @override
  ConsumerState<_DatetimePollField> createState() => _DatetimePollFieldState();
}

class _DatetimePollFieldState extends ConsumerState<_DatetimePollField> {
  late Set<String> _selected;

  @override
  void initState() {
    super.initState();
    _selected = const {};
  }

  String _joinSelected() => _selected.join(',');

  void _toggle(String iso, bool? checked, FormFieldState<String> state) {
    setState(() {
      if (checked == true) {
        _selected = {..._selected, iso};
      } else {
        _selected = _selected.where((s) => s != iso).toSet();
      }
      state.didChange(_joinSelected());
    });
  }

  Widget _buildOption(
    BuildContext context,
    String iso,
    PollTally? tally,
    String? winnerIso,
    FormFieldState<String> state,
  ) {
    final theme = Theme.of(context);
    final label = _formatPollOption(iso);
    final count = tally?.tallies[iso] ?? 0;
    final total = tally?.totalResponses ?? 0;
    final isWinner =
        winnerIso != null && _normalizeIso(iso) == _normalizeIso(winnerIso);

    if (widget.isFinalized) {
      return _PollOptionResult(
        label: label,
        count: count,
        total: total,
        isWinner: isWinner,
      );
    }

    return CheckboxListTile(
      title: _PollOptionTitle(
        label: label,
        count: count,
        textColor: theme.colorScheme.onSurface,
      ),
      value: _selected.contains(iso),
      onChanged: (checked) => _toggle(iso, checked, state),
      dense: true,
      contentPadding: EdgeInsets.zero,
    );
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final talliesAsync = ref.watch(pollTalliesProvider(widget.survey.id));
    final tallies = talliesAsync.valueOrNull;
    final questionTallies =
        tallies?.where((t) => t.questionId == widget.question.id).firstOrNull;
    final winnerIso =
        widget.survey.pollResult?.winningDatetime.toUtc().toIso8601String();

    return FormField<String>(
      initialValue: '',
      validator: widget.validator,
      onSaved: (_) => widget.onSaved(_joinSelected()),
      builder: (state) {
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              '${widget.question.label}${widget.question.required ? ' *' : ''}',
            ),
            const SizedBox(height: 8),
            if (!widget.isFinalized)
              Text(
                'select all times that work for you',
                style: TextStyle(
                  fontSize: 12,
                  color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
                ),
              ),
            const SizedBox(height: 8),
            ...widget.question.options.map(
              (iso) =>
                  _buildOption(context, iso, questionTallies, winnerIso, state),
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
}

/// Normalises an ISO 8601 string for comparison (strips trailing Z vs +00:00 etc.)
String _normalizeIso(String iso) {
  try {
    return DateTime.parse(iso).toUtc().toIso8601String();
  } catch (_) {
    return iso;
  }
}

class _PollOptionTitle extends StatelessWidget {
  final String label;
  final int count;
  final Color textColor;

  const _PollOptionTitle({
    required this.label,
    required this.count,
    required this.textColor,
  });

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Expanded(child: Text(label)),
        if (count > 0)
          Text(
            '$count vote${count == 1 ? '' : 's'}',
            style: TextStyle(
              fontSize: 12,
              color: textColor.withValues(alpha: 0.5),
            ),
          ),
      ],
    );
  }
}

class _PollOptionResult extends StatelessWidget {
  final String label;
  final int count;
  final int total;
  final bool isWinner;

  const _PollOptionResult({
    required this.label,
    required this.count,
    required this.total,
    required this.isWinner,
  });

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final fraction = total > 0 ? count / total : 0.0;

    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Container(
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color:
              isWinner
                  ? theme.colorScheme.primaryContainer.withValues(alpha: 0.6)
                  : theme.colorScheme.surfaceContainerHighest.withValues(
                    alpha: 0.4,
                  ),
          borderRadius: BorderRadius.circular(8),
          border:
              isWinner
                  ? Border.all(
                    color: theme.colorScheme.primary.withValues(alpha: 0.4),
                  )
                  : null,
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    label,
                    style: TextStyle(
                      fontWeight:
                          isWinner ? FontWeight.w600 : FontWeight.normal,
                    ),
                  ),
                ),
                if (isWinner)
                  Icon(
                    Icons.check_circle_rounded,
                    size: 16,
                    color: theme.colorScheme.primary,
                  ),
                const SizedBox(width: 4),
                Text(
                  '$count vote${count == 1 ? '' : 's'}',
                  style: TextStyle(
                    fontSize: 13,
                    color: theme.colorScheme.onSurface.withValues(alpha: 0.6),
                  ),
                ),
              ],
            ),
            const SizedBox(height: 6),
            ClipRRect(
              borderRadius: BorderRadius.circular(4),
              child: LinearProgressIndicator(
                value: fraction,
                minHeight: 6,
                backgroundColor: theme.colorScheme.outline.withValues(
                  alpha: 0.15,
                ),
                color:
                    isWinner
                        ? theme.colorScheme.primary
                        : theme.colorScheme.secondary,
              ),
            ),
          ],
        ),
      ),
    );
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
