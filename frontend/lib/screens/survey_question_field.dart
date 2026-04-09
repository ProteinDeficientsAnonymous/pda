import 'package:flutter/material.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/screens/survey_datetime_poll_field.dart';
import 'package:pda/config/constants.dart';

class SurveyQuestionField extends StatelessWidget {
  final SurveyQuestion question;
  final Survey survey;
  final bool isFinalized;
  final FormFieldSetter<String> onSaved;

  const SurveyQuestionField({
    super.key,
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
      return SurveyDatetimePollField(
        question: question,
        survey: survey,
        isFinalized: isFinalized,
        validator: _validate,
        onSaved: onSaved,
      );
    }

    return switch (question.fieldType) {
      FieldType.textarea => TextFormField(
        decoration: InputDecoration(labelText: label),
        maxLines: 4,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.select => SurveyRadioField(
        label: label,
        options: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.multiselect => SurveyCheckboxField(
        label: label,
        options: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.dropdown => SurveyDropdownField(
        label: label,
        options: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.number => TextFormField(
        decoration: InputDecoration(labelText: label),
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
      FieldType.yesNo => SurveyRadioField(
        label: label,
        options: const ['yes', 'no'],
        validator: _validate,
        onSaved: onSaved,
      ),
      FieldType.rating => SurveyRatingField(
        label: label,
        ratingLabels: question.options,
        validator: _validate,
        onSaved: onSaved,
      ),
      _ => TextFormField(
        decoration: InputDecoration(labelText: label),
        validator: _validate,
        onSaved: onSaved,
      ),
    };
  }
}

class SurveyRadioField extends FormField<String> {
  SurveyRadioField({
    super.key,
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
                   children: options
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

class SurveyCheckboxField extends FormField<String> {
  SurveyCheckboxField({
    super.key,
    required String label,
    required List<String> options,
    required FormFieldValidator<String> validator,
    required FormFieldSetter<String> onSaved,
  }) : super(
         initialValue: '',
         validator: validator,
         onSaved: onSaved,
         builder: (state) {
           final selected = (state.value ?? '')
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

class SurveyDropdownField extends StatelessWidget {
  final String label;
  final List<String> options;
  final FormFieldValidator<String> validator;
  final FormFieldSetter<String> onSaved;

  const SurveyDropdownField({
    super.key,
    required this.label,
    required this.options,
    required this.validator,
    required this.onSaved,
  });

  @override
  Widget build(BuildContext context) {
    return DropdownButtonFormField<String>(
      decoration: InputDecoration(labelText: label),
      items: options
          .map((o) => DropdownMenuItem(value: o, child: Text(o)))
          .toList(),
      validator: validator,
      onSaved: onSaved,
      onChanged: (_) {},
    );
  }
}

class SurveyRatingField extends FormField<String> {
  SurveyRatingField({
    super.key,
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
                         color: star <= current
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
