import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter/services.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/loading_button.dart';
import 'package:pda/widgets/phone_form_field.dart';

class AddMemberDialog extends StatefulWidget {
  final List<Role> allRoles;

  const AddMemberDialog({super.key, required this.allRoles});

  @override
  State<AddMemberDialog> createState() => _AddMemberDialogState();
}

class _AddMemberDialogState extends State<AddMemberDialog> {
  final _formKey = GlobalKey<FormState>();
  final _displayNameCtrl = TextEditingController();
  final _displayNameFocus = FocusNode();
  String _phoneNumber = '';
  String? _selectedRoleId;

  @override
  void dispose() {
    _displayNameCtrl.dispose();
    _displayNameFocus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Add member'),
      content: SizedBox(
        width: 440,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                PhoneFormField(
                  onChanged: (number) => _phoneNumber = number,
                  textInputAction: TextInputAction.done,
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
                    border: OutlineInputBorder(),
                  ),
                  validator: v.maxLength(64),
                  onFieldSubmitted: (_) {
                    if (!_formKey.currentState!.validate()) return;
                    Navigator.of(context).pop({
                      'phone_number': _phoneNumber,
                      'display_name': _displayNameCtrl.text.trim(),
                      if (_selectedRoleId != null) 'role_id': _selectedRoleId,
                    });
                  },
                ),
                if (widget.allRoles.isNotEmpty) ...[
                  const SizedBox(height: 12),
                  DropdownButtonFormField<String>(
                    initialValue: _selectedRoleId,
                    decoration: const InputDecoration(
                      labelText: 'Role (optional)',
                      border: OutlineInputBorder(),
                    ),
                    items: widget.allRoles
                        .map(
                          (r) => DropdownMenuItem(
                            value: r.id,
                            child: Text(r.name),
                          ),
                        )
                        .toList(),
                    onChanged: (val) => setState(() => _selectedRoleId = val),
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
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () {
            if (!_formKey.currentState!.validate()) return;
            Navigator.of(context).pop({
              'phone_number': _phoneNumber,
              'display_name': _displayNameCtrl.text.trim(),
              if (_selectedRoleId != null) 'role_id': _selectedRoleId,
            });
          },
          child: const Text('Create'),
        ),
      ],
    );
  }
}

class BulkAddDialog extends StatefulWidget {
  final WidgetRef ref;

  const BulkAddDialog({super.key, required this.ref});

  @override
  State<BulkAddDialog> createState() => _BulkAddDialogState();
}

class _BulkAddDialogState extends State<BulkAddDialog> {
  final _ctrl = TextEditingController();
  bool _loading = false;
  Map<String, dynamic>? _results;

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  List<String> get _phones => _ctrl.text
      .split('\n')
      .map((l) => l.trim())
      .where((l) => l.isNotEmpty)
      .toList();

  Future<void> _submit() async {
    final phones = _phones;
    if (phones.isEmpty) return;
    setState(() => _loading = true);
    try {
      final data = await widget.ref
          .read(userManagementProvider.notifier)
          .bulkCreateUsers(phones);
      setState(() {
        _results = data;
        _loading = false;
      });
    } catch (e) {
      setState(() => _loading = false);
      if (mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('Bulk add members'),
      content: SizedBox(
        width: 480,
        child: _results != null ? _buildResults(context) : _buildForm(context),
      ),
      actions: _results != null
          ? [
              TextButton(
                onPressed: () => Navigator.of(context).pop(),
                child: const Text('Done'),
              ),
            ]
          : [
              TextButton(
                onPressed: _loading ? null : () => Navigator.of(context).pop(),
                child: const Text('Cancel'),
              ),
              LoadingButton(
                label:
                    'Add ${_phones.length} member${_phones.length == 1 ? '' : 's'}',
                onPressed: _phones.isEmpty ? null : _submit,
                loading: _loading,
              ),
            ],
    );
  }

  Widget _buildForm(BuildContext context) {
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'One phone number per line. Members will be prompted to set a display name and password on first login.',
          style: TextStyle(fontSize: 13, color: Colors.grey),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: _ctrl,
          maxLines: 8,
          onChanged: (_) => setState(() {}),
          decoration: const InputDecoration(
            border: OutlineInputBorder(),
            hintText: '+12125551234\n+13105559876\n…',
            alignLabelWithHint: true,
          ),
          style: const TextStyle(fontFamily: 'monospace', fontSize: 14),
        ),
      ],
    );
  }

  Widget _buildResults(BuildContext context) {
    final results = (_results!['results'] as List).cast<Map<String, dynamic>>();
    final created = _results!['created'] as int;
    final failed = _results!['failed'] as int;
    final origin = Uri.base.origin;

    return SingleChildScrollView(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            '$created created${failed > 0 ? ', $failed failed' : ''}',
            style: TextStyle(
              fontWeight: FontWeight.bold,
              color: failed > 0
                  ? Theme.of(context).colorScheme.error
                  : Theme.of(context).colorScheme.primary,
            ),
          ),
          if (created > 0) ...[
            const SizedBox(height: 12),
            const Text('Login links (share with each new member):'),
            const SizedBox(height: 6),
            ...results
                .where(
                  (r) => r['success'] == true && r['magic_link_token'] != null,
                )
                .map(
                  (r) => Padding(
                    padding: const EdgeInsets.only(bottom: 8),
                    child: _MagicLinkRow(
                      phone: r['phone_number'] as String,
                      url: '$origin/magic-login/${r['magic_link_token']}',
                    ),
                  ),
                ),
          ],
          if (failed > 0) ...[
            const SizedBox(height: 12),
            const Text(
              'Errors:',
              style: TextStyle(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 4),
            ...results
                .where((r) => r['success'] == false)
                .map(
                  (r) => Padding(
                    padding: const EdgeInsets.only(bottom: 4),
                    child: Text(
                      'Row ${r['row']}: ${r['phone_number']} — ${r['error']}',
                      style: TextStyle(
                        fontSize: 13,
                        color: Theme.of(context).colorScheme.error,
                      ),
                    ),
                  ),
                ),
          ],
        ],
      ),
    );
  }
}

class _MagicLinkRow extends StatelessWidget {
  final String phone;
  final String url;

  const _MagicLinkRow({required this.phone, required this.url});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(phone, style: const TextStyle(fontSize: 12, color: Colors.grey)),
        const SizedBox(height: 2),
        Container(
          decoration: BoxDecoration(
            border: Border.all(color: Colors.grey.shade300),
            borderRadius: BorderRadius.circular(6),
          ),
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          child: Row(
            children: [
              Expanded(
                child: Text(
                  url,
                  style: const TextStyle(fontSize: 11, fontFamily: 'monospace'),
                  overflow: TextOverflow.ellipsis,
                ),
              ),
              const SizedBox(width: 6),
              InkWell(
                onTap: () => Clipboard.setData(ClipboardData(text: url)),
                borderRadius: BorderRadius.circular(4),
                child: Padding(
                  padding: const EdgeInsets.all(4),
                  child: Icon(
                    Icons.content_copy_outlined,
                    size: 14,
                    color: Colors.grey.shade600,
                  ),
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}
