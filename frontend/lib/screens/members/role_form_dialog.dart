import 'package:flutter/material.dart';
import 'package:pda/models/user.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/config/constants.dart';

const kPermissionLabels = {
  Permission.createUser: 'Create user',
  Permission.manageUsers: 'Manage users',
  Permission.manageRoles: 'Manage roles',
  Permission.approveJoinRequests: 'Approve join requests',
  Permission.manageEvents: 'Manage events',
  Permission.editGuidelines: 'Edit community guidelines',
  Permission.manageWhatsapp: 'Manage WhatsApp',
  Permission.editFaq: 'Edit FAQ',
  Permission.editHomepage: 'Edit homepage',
  Permission.editJoinQuestions: 'Edit join form questions',
  Permission.manageSurveys: 'Manage surveys',
  Permission.tagOfficialEvent: 'Tag official event',
};

// Dialog to create or edit a role (name + permission checkboxes)
class RoleFormDialog extends StatefulWidget {
  final Role? role;

  const RoleFormDialog({super.key, this.role});

  @override
  State<RoleFormDialog> createState() => _RoleFormDialogState();
}

class _RoleFormDialogState extends State<RoleFormDialog> {
  final _formKey = GlobalKey<FormState>();
  late final TextEditingController _name;
  late Set<String> _selectedPermissions;

  bool get _isEdit => widget.role != null;

  @override
  void initState() {
    super.initState();
    _name = TextEditingController(text: widget.role?.name ?? '');
    _selectedPermissions = Set.from(widget.role?.permissions ?? []);
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(_isEdit ? 'Edit role' : 'New role'),
      content: SizedBox(
        width: 400,
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                if (!_isEdit)
                  TextFormField(
                    controller: _name,
                    textInputAction: TextInputAction.done,
                    decoration: const InputDecoration(labelText: 'Role name *'),
                    validator: v.roleName(),
                    onFieldSubmitted: (_) {
                      if (!_formKey.currentState!.validate()) return;
                      Navigator.of(context).pop({
                        'name': _name.text.trim(),
                        'permissions': _selectedPermissions.toList(),
                      });
                    },
                  ),
                if (!_isEdit) const SizedBox(height: 16),
                Text(
                  'Permissions',
                  style: Theme.of(context).textTheme.labelLarge,
                ),
                const SizedBox(height: 4),
                ...kPermissionLabels.entries.map((entry) {
                  return CheckboxListTile(
                    value: _selectedPermissions.contains(entry.key),
                    onChanged: (v) => setState(() {
                      if (v == true) {
                        _selectedPermissions.add(entry.key);
                      } else {
                        _selectedPermissions.remove(entry.key);
                      }
                    }),
                    title: Text(entry.value),
                    dense: true,
                    contentPadding: EdgeInsets.zero,
                  );
                }),
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
              'name': _name.text.trim(),
              'permissions': _selectedPermissions.toList(),
            });
          },
          child: Text(_isEdit ? 'Save' : 'Create'),
        ),
      ],
    );
  }
}

// Dialog to assign/remove roles from a user
class RoleEditorDialog extends StatefulWidget {
  final User user;
  final List<Role> allRoles;
  final bool isOwnAccount;
  final String adminRoleId;
  final bool isLastAdmin;
  final String? currentUserId;

  const RoleEditorDialog({
    super.key,
    required this.user,
    required this.allRoles,
    required this.isOwnAccount,
    required this.adminRoleId,
    required this.isLastAdmin,
    required this.currentUserId,
  });

  @override
  State<RoleEditorDialog> createState() => _RoleEditorDialogState();
}

class _RoleEditorDialogState extends State<RoleEditorDialog> {
  late Set<String> _selected;

  @override
  void initState() {
    super.initState();
    _selected = widget.user.roles.map((r) => r.id).toSet();
  }

  bool _isLocked(Role role) {
    if (role.id != widget.adminRoleId) return false;
    if (widget.isLastAdmin && _selected.contains(role.id)) return true;
    if (widget.isOwnAccount && _selected.contains(role.id)) return true;
    return false;
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: Text(
        'Edit roles — ${widget.user.displayName.isNotEmpty ? widget.user.displayName : widget.user.phoneNumber}',
      ),
      content: SizedBox(
        width: 400,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: widget.allRoles.map((role) {
              final locked = _isLocked(role);
              final checked = _selected.contains(role.id);
              return CheckboxListTile(
                value: checked,
                onChanged: locked
                    ? null
                    : (v) => setState(() {
                        if (v == true) {
                          _selected.add(role.id);
                        } else {
                          _selected.remove(role.id);
                        }
                      }),
                title: Row(
                  children: [
                    Text(role.name),
                    if (locked) ...[
                      const SizedBox(width: 6),
                      Icon(
                        Icons.lock_outline,
                        size: 14,
                        color: Colors.grey[500],
                      ),
                    ],
                  ],
                ),
                subtitle: role.permissions.isEmpty
                    ? null
                    : Text(
                        role.permissions
                            .map((p) => kPermissionLabels[p] ?? p)
                            .join(', '),
                        style: const TextStyle(fontSize: 11),
                      ),
              );
            }).toList(),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(
          onPressed: () => Navigator.of(context).pop(_selected.toList()),
          child: const Text('Save'),
        ),
      ],
    );
  }
}
