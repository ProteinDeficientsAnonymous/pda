import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/user.dart';
import 'package:pda/providers/user_management_provider.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/loading_button.dart';
import 'bulk_add_form.dart';
import 'single_add_form.dart';

export 'bulk_add_form.dart' show MagicLinkRow;

final _log = Logger('AddMember');

enum _AddMode { single, bulk }

class AddMemberDialog extends ConsumerStatefulWidget {
  final List<Role> allRoles;

  const AddMemberDialog({super.key, required this.allRoles});

  @override
  ConsumerState<AddMemberDialog> createState() => _AddMemberDialogState();
}

class _AddMemberDialogState extends ConsumerState<AddMemberDialog> {
  _AddMode _mode = _AddMode.single;

  // Single-add state
  final _formKey = GlobalKey<FormState>();
  String _phoneNumber = '';
  String _displayName = '';
  String? _roleId;
  bool _singleLoading = false;
  Map<String, dynamic>? _singleResult;

  // Bulk-add state
  final _bulkCtrl = TextEditingController();
  bool _bulkLoading = false;
  Map<String, dynamic>? _bulkResults;

  @override
  void dispose() {
    _bulkCtrl.dispose();
    super.dispose();
  }

  List<String> get _phones => _bulkCtrl.text
      .split('\n')
      .map((l) => l.trim())
      .where((l) => l.isNotEmpty)
      .toList();

  bool get _showingResults => _singleResult != null || _bulkResults != null;

  Future<void> _submitSingle() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _singleLoading = true);
    try {
      final data = await ref
          .read(userManagementProvider.notifier)
          .createUser(
            phoneNumber: _phoneNumber,
            displayName: _displayName,
            roleId: _roleId,
          );
      _log.info('member creation succeeded for $_phoneNumber');
      setState(() {
        _singleResult = data;
        _singleLoading = false;
      });
    } catch (e, st) {
      _log.warning('failed to create member for $_phoneNumber', e, st);
      setState(() => _singleLoading = false);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    }
  }

  Future<void> _submitBulk() async {
    final phones = _phones;
    if (phones.isEmpty) return;
    setState(() => _bulkLoading = true);
    try {
      final data = await ref
          .read(userManagementProvider.notifier)
          .bulkCreateUsers(phones);
      _log.info('bulk add succeeded: ${phones.length} phones submitted');
      setState(() {
        _bulkResults = data;
        _bulkLoading = false;
      });
    } catch (e, st) {
      _log.warning('failed to bulk add members', e, st);
      setState(() => _bulkLoading = false);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      title: const Text('add member'),
      content: SizedBox(
        width: 480,
        child: SingleChildScrollView(
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              if (!_showingResults) ...[
                SegmentedButton<_AddMode>(
                  segments: const [
                    ButtonSegment(
                      value: _AddMode.single,
                      label: Text('single'),
                    ),
                    ButtonSegment(value: _AddMode.bulk, label: Text('bulk')),
                  ],
                  selected: {_mode},
                  onSelectionChanged: (s) => setState(() => _mode = s.first),
                  showSelectedIcon: false,
                  style: const ButtonStyle(
                    visualDensity: VisualDensity(
                      horizontal: VisualDensity.minimumDensity,
                      vertical: VisualDensity.minimumDensity,
                    ),
                  ),
                ),
                const SizedBox(height: 16),
              ],
              if (_mode == _AddMode.single) _buildSingleBody(),
              if (_mode == _AddMode.bulk) _buildBulkBody(),
            ],
          ),
        ),
      ),
      actions: _buildActions(),
    );
  }

  Widget _buildSingleBody() {
    if (_singleResult != null) {
      return _SingleSuccessView(data: _singleResult!);
    }
    return SingleAddForm(
      allRoles: widget.allRoles,
      formKey: _formKey,
      onPhoneChanged: (v) => _phoneNumber = v,
      onDisplayNameChanged: (v) => _displayName = v,
      onRoleChanged: (v) => _roleId = v,
    );
  }

  Widget _buildBulkBody() {
    if (_bulkResults != null) {
      return BulkAddResults(results: _bulkResults!);
    }
    return BulkAddForm(controller: _bulkCtrl, onChanged: () => setState(() {}));
  }

  List<Widget> _buildActions() {
    if (_showingResults) {
      return [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('done'),
        ),
      ];
    }
    if (_mode == _AddMode.single) {
      return [
        TextButton(
          onPressed: _singleLoading ? null : () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        LoadingButton(
          label: 'create',
          onPressed: _submitSingle,
          loading: _singleLoading,
        ),
      ];
    }
    // bulk mode
    final count = _phones.length;
    return [
      TextButton(
        onPressed: _bulkLoading ? null : () => Navigator.of(context).pop(),
        child: const Text('cancel'),
      ),
      LoadingButton(
        label: 'add $count member${count == 1 ? '' : 's'}',
        onPressed: count == 0 ? null : _submitBulk,
        loading: _bulkLoading,
      ),
    ];
  }
}

class _SingleSuccessView extends StatelessWidget {
  final Map<String, dynamic> data;

  const _SingleSuccessView({required this.data});

  @override
  Widget build(BuildContext context) {
    final displayName =
        data['display_name'] as String? ?? data['phone_number'] as String;
    final token = data['magic_link_token'] as String;
    final url = '${Uri.base.origin}/magic-login/$token';

    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text('$displayName has been added — share their login link:'),
        const SizedBox(height: 12),
        const Text(
          'login link',
          style: TextStyle(fontSize: 12, color: Colors.grey),
        ),
        const SizedBox(height: 4),
        _MagicLinkField(url: url),
        const SizedBox(height: 12),
        OutlinedButton.icon(
          onPressed: () {
            final message =
                'hey! you\'ve been added to PDA 🌱\n\n'
                'click here to log in: $url\n\n'
                'the link works once and expires in 7 days — '
                'you\'ll set your password on first login';
            Clipboard.setData(ClipboardData(text: message));
            showSnackBar(context, 'welcome message copied ✓');
          },
          icon: const Icon(Icons.content_copy_outlined, size: 16),
          label: const Text('copy welcome message'),
        ),
        const SizedBox(height: 8),
        Text(
          'includes login link — expires in 7 days',
          style: TextStyle(color: Colors.grey.shade500, fontSize: 12),
        ),
      ],
    );
  }
}

class _MagicLinkField extends StatelessWidget {
  final String url;

  const _MagicLinkField({required this.url});

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        border: Border.all(color: Colors.grey.shade300),
        borderRadius: BorderRadius.circular(6),
      ),
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 8),
      child: Row(
        children: [
          Expanded(
            child: Text(
              url,
              style: const TextStyle(fontSize: 12, fontFamily: 'monospace'),
              overflow: TextOverflow.ellipsis,
            ),
          ),
          const SizedBox(width: 8),
          InkWell(
            onTap: () => Clipboard.setData(ClipboardData(text: url)),
            borderRadius: BorderRadius.circular(4),
            child: Padding(
              padding: const EdgeInsets.all(4),
              child: Icon(
                Icons.content_copy_outlined,
                size: 16,
                color: Colors.grey.shade600,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
