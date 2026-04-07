import 'package:flutter/material.dart';
import 'package:intl/intl.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/widgets/date_time_picker_dialog.dart';

final _log = Logger('SurveyQuestionForm');

class SurveyQuestionFormResult {
  final String label;
  final String fieldType;
  final List<String> options;
  final bool required;

  const SurveyQuestionFormResult({
    required this.label,
    required this.fieldType,
    required this.options,
    required this.required,
  });
}

const surveyFieldTypeLabels = {
  FieldType.text: 'text',
  FieldType.textarea: 'text area',
  FieldType.select: 'single select',
  FieldType.multiselect: 'multi select',
  FieldType.dropdown: 'dropdown',
  FieldType.number: 'number',
  FieldType.yesNo: 'yes / no',
  FieldType.rating: 'rating (1–5)',
  FieldType.datetimePoll: 'datetime poll',
};

const _fieldTypesWithOptions = {
  FieldType.select,
  FieldType.multiselect,
  FieldType.dropdown,
};

String formatSurveyDatetimeOption(String iso) {
  try {
    final dt = DateTime.parse(iso).toLocal();
    return DateFormat('EEE, MMM d · h:mm a').format(dt).toLowerCase();
  } catch (e, st) {
    _log.warning('failed to parse datetime option: $iso', e, st);
    return iso;
  }
}

class SurveyQuestionFormDialog extends StatefulWidget {
  final SurveyQuestion? question;

  const SurveyQuestionFormDialog({super.key, this.question});

  @override
  State<SurveyQuestionFormDialog> createState() =>
      _SurveyQuestionFormDialogState();
}

class _SurveyQuestionFormDialogState extends State<SurveyQuestionFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _labelCtrl;
  late String _fieldType;
  late bool _required;
  late List<TextEditingController> _optionCtrls;
  late List<TextEditingController> _ratingLabelCtrls;
  late List<DateTime> _datetimeOptions;

  @override
  void initState() {
    super.initState();
    _labelCtrl = TextEditingController(text: widget.question?.label ?? '');
    _fieldType = widget.question?.fieldType ?? FieldType.text;
    _required = widget.question?.required ?? false;
    final existingOptions = widget.question?.options ?? [];
    _optionCtrls = existingOptions
        .map((o) => TextEditingController(text: o))
        .toList();
    _ratingLabelCtrls = List.generate(
      5,
      (i) => TextEditingController(
        text: (_fieldType == FieldType.rating && i < existingOptions.length)
            ? existingOptions[i]
            : '',
      ),
    );
    _datetimeOptions = (_fieldType == FieldType.datetimePoll)
        ? existingOptions
              .map((s) {
                try {
                  return DateTime.parse(s).toLocal();
                } catch (e, st) {
                  _log.warning(
                    'failed to parse datetime option in initState: $s',
                    e,
                    st,
                  );
                  return null;
                }
              })
              .whereType<DateTime>()
              .toList()
        : [];
  }

  @override
  void dispose() {
    _labelCtrl.dispose();
    for (final c in _optionCtrls) {
      c.dispose();
    }
    for (final c in _ratingLabelCtrls) {
      c.dispose();
    }
    super.dispose();
  }

  bool get _showOptions => _fieldTypesWithOptions.contains(_fieldType);

  void _addOption() {
    setState(() => _optionCtrls.add(TextEditingController()));
  }

  void _removeOption(int index) {
    setState(() {
      _optionCtrls[index].dispose();
      _optionCtrls.removeAt(index);
    });
  }

  Future<void> _addDatetimeOption() async {
    final now = DateTime.now();
    final dt = await showDateTimePicker(
      context: context,
      initialDateTime: now,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 2),
    );
    if (dt == null || !mounted) return;
    setState(() {
      _datetimeOptions.add(dt);
    });
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    List<String> options;
    if (_fieldType == FieldType.datetimePoll) {
      options = _datetimeOptions
          .map((dt) => dt.toUtc().toIso8601String())
          .toList();
    } else if (_fieldType == FieldType.rating) {
      options = _ratingLabelCtrls.map((c) => c.text.trim()).toList();
    } else if (_showOptions) {
      options = _optionCtrls
          .map((c) => c.text.trim())
          .where((o) => o.isNotEmpty)
          .toList();
    } else {
      options = [];
    }
    Navigator.of(context).pop(
      SurveyQuestionFormResult(
        label: _labelCtrl.text.trim(),
        fieldType: _fieldType,
        options: options,
        required: _required,
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final isEditing = widget.question != null;
    return AlertDialog(
      title: Text(isEditing ? 'edit question' : 'add question'),
      contentPadding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextFormField(
                  controller: _labelCtrl,
                  decoration: const InputDecoration(
                    labelText: 'question label',
                    border: OutlineInputBorder(),
                  ),
                  autofocus: true,
                  textInputAction: TextInputAction.done,
                  validator: (v) {
                    if (v == null || v.trim().isEmpty) return 'Required';
                    return null;
                  },
                  onFieldSubmitted: (_) => _submit(),
                ),
                const SizedBox(height: 16),
                DropdownButtonFormField<String>(
                  initialValue: _fieldType,
                  decoration: const InputDecoration(
                    labelText: 'field type',
                    border: OutlineInputBorder(),
                  ),
                  items: surveyFieldTypeLabels.entries
                      .map(
                        (e) => DropdownMenuItem(
                          value: e.key,
                          child: Text(e.value),
                        ),
                      )
                      .toList(),
                  onChanged: (val) =>
                      setState(() => _fieldType = val ?? FieldType.text),
                ),
                const SizedBox(height: 12),
                SwitchListTile(
                  title: const Text('required'),
                  value: _required,
                  contentPadding: EdgeInsets.zero,
                  onChanged: (val) => setState(() => _required = val),
                ),
                if (_showOptions) ...[
                  const SizedBox(height: 12),
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'options',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  const SizedBox(height: 8),
                  for (var i = 0; i < _optionCtrls.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        children: [
                          Expanded(
                            child: TextFormField(
                              controller: _optionCtrls[i],
                              decoration: InputDecoration(
                                hintText: 'option ${i + 1}',
                                isDense: true,
                              ),
                            ),
                          ),
                          IconButton(
                            tooltip: 'remove option',
                            icon: const Icon(Icons.close, size: 18),
                            onPressed: () => _removeOption(i),
                          ),
                        ],
                      ),
                    ),
                  TextButton.icon(
                    onPressed: _addOption,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('add option'),
                  ),
                ],
                if (_fieldType == FieldType.datetimePoll) ...[
                  const SizedBox(height: 12),
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'datetime options',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'add the date/time options members will vote on',
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                  const SizedBox(height: 8),
                  for (var i = 0; i < _datetimeOptions.length; i++)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: Row(
                        children: [
                          const Icon(Icons.event_outlined, size: 16),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              formatSurveyDatetimeOption(
                                _datetimeOptions[i].toIso8601String(),
                              ),
                              style: const TextStyle(fontSize: 13),
                            ),
                          ),
                          IconButton(
                            tooltip: 'remove option',
                            icon: const Icon(Icons.close, size: 18),
                            onPressed: () =>
                                setState(() => _datetimeOptions.removeAt(i)),
                          ),
                        ],
                      ),
                    ),
                  TextButton.icon(
                    onPressed: _addDatetimeOption,
                    icon: const Icon(Icons.add, size: 18),
                    label: const Text('add date & time'),
                  ),
                ],
                if (_fieldType == FieldType.rating) ...[
                  const SizedBox(height: 12),
                  const Align(
                    alignment: Alignment.centerLeft,
                    child: Text(
                      'rating labels (optional)',
                      style: TextStyle(fontWeight: FontWeight.w600),
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'label each star level — leave blank to skip',
                    style: TextStyle(
                      fontSize: 12,
                      color: Theme.of(
                        context,
                      ).colorScheme.onSurface.withValues(alpha: 0.5),
                    ),
                  ),
                  const SizedBox(height: 8),
                  for (var i = 0; i < 5; i++)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 8),
                      child: TextFormField(
                        controller: _ratingLabelCtrls[i],
                        decoration: InputDecoration(
                          hintText: '${i + 1} star${i == 0 ? '' : 's'}',
                          prefixText: '${'★' * (i + 1)}  ',
                          isDense: true,
                        ),
                      ),
                    ),
                ],
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        FilledButton(
          onPressed: _submit,
          child: Text(isEditing ? 'save' : 'add'),
        ),
      ],
    );
  }
}
