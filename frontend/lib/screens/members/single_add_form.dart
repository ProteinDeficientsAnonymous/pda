import 'package:flutter/material.dart';
import 'package:pda/models/user.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/phone_form_field.dart';

class SingleAddForm extends StatefulWidget {
  final List<Role> allRoles;
  final GlobalKey<FormState> formKey;
  final ValueChanged<String> onPhoneChanged;
  final ValueChanged<String> onDisplayNameChanged;
  final ValueChanged<String?> onRoleChanged;

  const SingleAddForm({
    super.key,
    required this.allRoles,
    required this.formKey,
    required this.onPhoneChanged,
    required this.onDisplayNameChanged,
    required this.onRoleChanged,
  });

  @override
  State<SingleAddForm> createState() => _SingleAddFormState();
}

class _SingleAddFormState extends State<SingleAddForm> {
  final _displayNameCtrl = TextEditingController();
  final _displayNameFocus = FocusNode();
  String? _selectedRoleId;

  @override
  void dispose() {
    _displayNameCtrl.dispose();
    _displayNameFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Form(
      key: widget.formKey,
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          PhoneFormField(
            onChanged: widget.onPhoneChanged,
            textInputAction: TextInputAction.next,
            onFieldSubmitted: (_) => _displayNameFocus.requestFocus(),
          ),
          const SizedBox(height: 12),
          TextFormField(
            controller: _displayNameCtrl,
            focusNode: _displayNameFocus,
            keyboardType: TextInputType.name,
            textInputAction: TextInputAction.done,
            decoration: const InputDecoration(
              labelText: 'Display name (optional)',
            ),
            validator: v.optionalDisplayName(),
            onChanged: widget.onDisplayNameChanged,
          ),
          if (widget.allRoles.isNotEmpty) ...[
            const SizedBox(height: 12),
            DropdownButtonFormField<String>(
              initialValue: _selectedRoleId,
              decoration: const InputDecoration(labelText: 'Role (optional)'),
              items: widget.allRoles
                  .map(
                    (r) => DropdownMenuItem(value: r.id, child: Text(r.name)),
                  )
                  .toList(),
              onChanged: (val) {
                setState(() => _selectedRoleId = val);
                widget.onRoleChanged(val);
              },
            ),
          ],
        ],
      ),
    );
  }
}
