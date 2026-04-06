import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/utils/snackbar.dart';

class InviteModal extends ConsumerStatefulWidget {
  final Event event;

  const InviteModal({super.key, required this.event});

  @override
  ConsumerState<InviteModal> createState() => _InviteModalState();
}

class _InviteModalState extends ConsumerState<InviteModal> {
  final _searchController = TextEditingController();
  List<_UserResult> _results = [];
  late Set<String> _selectedIds;
  late Set<String> _initialIds;
  bool _searching = false;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _initialIds = Set<String>.from(widget.event.invitedUserIds);
    _selectedIds = Set<String>.from(widget.event.invitedUserIds);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  Future<void> _search(String q) async {
    if (q.trim().isEmpty) {
      setState(() => _results = []);
      return;
    }
    setState(() => _searching = true);
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.get(
        '/api/auth/users/search/',
        queryParameters: {'q': q.trim()},
      );
      final data = (resp.data as List<dynamic>?) ?? [];
      if (mounted) {
        setState(() {
          _results = data
              .map(
                (item) => _UserResult(
                  id: item['id'] as String,
                  name: item['display_name'] as String,
                  phone: item['phone_number'] as String,
                ),
              )
              .toList();
        });
      }
    } catch (_) {
      if (mounted) setState(() => _results = []);
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  Future<void> _submit() async {
    setState(() => _saving = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.patch(
        '/api/community/events/${widget.event.id}/',
        data: {'invited_user_ids': _selectedIds.toList()},
      );
      ref.invalidate(eventDetailProvider(widget.event.id));
      ref.invalidate(eventsProvider);
      if (mounted) {
        Navigator.of(context).pop();
        showSnackBar(context, 'invites updated 🌱');
      }
    } catch (_) {
      if (mounted) {
        setState(() => _saving = false);
        showErrorSnackBar(context, 'couldn\'t update invites — try again');
      }
    }
  }

  void _toggle(String id) {
    setState(() {
      if (_selectedIds.contains(id)) {
        _selectedIds.remove(id);
      } else {
        _selectedIds.add(id);
      }
    });
  }

  bool get _hasChanges =>
      !_selectedIds.containsAll(_initialIds) ||
      !_initialIds.containsAll(_selectedIds);

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Dialog(
      insetPadding: const EdgeInsets.symmetric(horizontal: 24, vertical: 40),
      child: ConstrainedBox(
        constraints: const BoxConstraints(maxWidth: 480, maxHeight: 560),
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Row(
                children: [
                  Text(
                    'invite friends',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const Spacer(),
                  IconButton(
                    icon: const Icon(Icons.close),
                    tooltip: 'close',
                    onPressed: () => Navigator.of(context).pop(),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              TextField(
                controller: _searchController,
                autofocus: true,
                decoration: InputDecoration(
                  hintText: 'search by name or phone…',
                  border: const OutlineInputBorder(),
                  isDense: true,
                  suffixIcon: _searching
                      ? const Padding(
                          padding: EdgeInsets.all(10),
                          child: SizedBox(
                            width: 16,
                            height: 16,
                            child: CircularProgressIndicator(strokeWidth: 2),
                          ),
                        )
                      : null,
                ),
                onChanged: _search,
              ),
              const SizedBox(height: 8),
              Expanded(
                child: _results.isEmpty
                    ? Center(
                        child: Text(
                          _searchController.text.isEmpty
                              ? 'search for members to invite'
                              : 'no results',
                          style: TextStyle(
                            color: cs.onSurfaceVariant,
                            fontSize: 13,
                          ),
                        ),
                      )
                    : ListView.builder(
                        itemCount: _results.length,
                        itemBuilder: (_, i) {
                          final r = _results[i];
                          final selected = _selectedIds.contains(r.id);
                          return CheckboxListTile(
                            dense: true,
                            value: selected,
                            onChanged: (_) => _toggle(r.id),
                            title: Text(r.name),
                            subtitle: Text(
                              r.phone,
                              style: TextStyle(
                                fontSize: 12,
                                color: cs.onSurfaceVariant,
                              ),
                            ),
                          );
                        },
                      ),
              ),
              const SizedBox(height: 12),
              FilledButton(
                onPressed: _hasChanges && !_saving ? _submit : null,
                child: _saving
                    ? const SizedBox(
                        height: 16,
                        width: 16,
                        child: CircularProgressIndicator(
                          strokeWidth: 2,
                          color: Colors.white,
                        ),
                      )
                    : const Text('invite'),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _UserResult {
  final String id;
  final String name;
  final String phone;

  const _UserResult({
    required this.id,
    required this.name,
    required this.phone,
  });
}
