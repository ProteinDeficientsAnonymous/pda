import 'package:flutter/material.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/join_form_question.dart';

class JoinFormQuestionResult {
  final String label;
  final String fieldType;
  final List<String> options;
  final bool required;

  const JoinFormQuestionResult({
    required this.label,
    required this.fieldType,
    required this.options,
    required this.required,
  });
}

class JoinFormQuestionDialog extends StatefulWidget {
  final JoinFormQuestion? question;

  const JoinFormQuestionDialog({super.key, this.question});

  @override
  State<JoinFormQuestionDialog> createState() => _JoinFormQuestionDialogState();
}

class _JoinFormQuestionDialogState extends State<JoinFormQuestionDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _labelCtrl;
  late String _fieldType;
  late bool _required;
  late List<TextEditingController> _optionCtrls;

  @override
  void initState() {
    super.initState();
    _labelCtrl = TextEditingController(text: widget.question?.label ?? '');
    _fieldType = widget.question?.fieldType ?? FieldType.text;
    _required = widget.question?.required ?? false;
    _optionCtrls = (widget.question?.options ?? [])
        .map((o) => TextEditingController(text: o))
        .toList();
  }

  @override
  void dispose() {
    _labelCtrl.dispose();
    for (final c in _optionCtrls) {
      c.dispose();
    }
    super.dispose();
  }

  void _addOption() {
    setState(() => _optionCtrls.add(TextEditingController()));
  }

  void _removeOption(int index) {
    setState(() {
      _optionCtrls[index].dispose();
      _optionCtrls.removeAt(index);
    });
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    final options = _fieldType == FieldType.select
        ? _optionCtrls
              .map((c) => c.text.trim())
              .where((o) => o.isNotEmpty)
              .toList()
        : <String>[];
    Navigator.of(context).pop(
      JoinFormQuestionResult(
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
      title: Text(isEditing ? 'Edit question' : 'Add question'),
      content: Form(
        key: _formKey,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              TextFormField(
                controller: _labelCtrl,
                decoration: const InputDecoration(labelText: 'Question label'),
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
                decoration: const InputDecoration(labelText: 'Field type'),
                items: const [
                  DropdownMenuItem(value: FieldType.text, child: Text('Text')),
                  DropdownMenuItem(
                    value: FieldType.select,
                    child: Text('Dropdown'),
                  ),
                ],
                onChanged: (val) =>
                    setState(() => _fieldType = val ?? FieldType.text),
              ),
              const SizedBox(height: 12),
              SwitchListTile(
                title: const Text('Required'),
                value: _required,
                contentPadding: EdgeInsets.zero,
                onChanged: (val) => setState(() => _required = val),
              ),
              if (_fieldType == FieldType.select) ...[
                const SizedBox(height: 12),
                const Align(
                  alignment: Alignment.centerLeft,
                  child: Text(
                    'Options',
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
                              hintText: 'Option ${i + 1}',
                              isDense: true,
                            ),
                          ),
                        ),
                        IconButton(
                          tooltip: 'Remove option',
                          icon: const Icon(Icons.close, size: 18),
                          onPressed: () => _removeOption(i),
                        ),
                      ],
                    ),
                  ),
                TextButton.icon(
                  onPressed: _addOption,
                  icon: const Icon(Icons.add, size: 18),
                  label: const Text('Add option'),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: _submit,
          child: Text(isEditing ? 'Save' : 'Add'),
        ),
      ],
    );
  }
}
