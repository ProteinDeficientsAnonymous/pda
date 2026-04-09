import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/calendar/event_form_models.dart';

final _log = Logger('CoHostPicker');

class CoHostPicker extends ConsumerStatefulWidget {
  final Set<String> selectedIds;
  final Map<String, String> selectedNames;
  final ValueChanged<Set<String>> onChanged;
  final ScrollController? scrollController;

  const CoHostPicker({
    super.key,
    required this.selectedIds,
    required this.selectedNames,
    required this.onChanged,
    this.scrollController,
  });

  @override
  ConsumerState<CoHostPicker> createState() => _CoHostPickerState();
}

class _CoHostPickerState extends ConsumerState<CoHostPicker> {
  final _controller = TextEditingController();
  List<CoHostResult> _results = [];
  bool _searching = false;
  late Map<String, String> _knownNames;

  @override
  void initState() {
    super.initState();
    _knownNames = Map<String, String>.from(widget.selectedNames);
  }

  @override
  void dispose() {
    _controller.dispose();
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
      setState(() {
        _results = data
            .map(
              (item) => CoHostResult(
                id: item['id'] as String,
                displayName: item['display_name'] as String,
                phone: item['phone_number'] as String,
              ),
            )
            .toList();
      });
      if (_results.isNotEmpty) {
        WidgetsBinding.instance.addPostFrameCallback((_) {
          final sc = widget.scrollController;
          if (sc != null && sc.hasClients) {
            sc.animateTo(
              sc.position.maxScrollExtent,
              duration: const Duration(milliseconds: 200),
              curve: Curves.easeOut,
            );
          }
        });
      }
    } catch (e, st) {
      _log.warning('search failed', e, st);
      setState(() => _results = []);
    } finally {
      if (mounted) setState(() => _searching = false);
    }
  }

  void _toggle(String id, String name) {
    _knownNames[id] = name;
    final next = Set<String>.from(widget.selectedIds);
    if (next.contains(id)) {
      next.remove(id);
    } else {
      next.add(id);
    }
    widget.onChanged(next);
  }

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final selected = widget.selectedIds;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        if (selected.isNotEmpty) ...[
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: selected.map((id) {
              final name = _knownNames[id] ?? id;
              return Chip(
                label: Text(name, style: const TextStyle(fontSize: 13)),
                onDeleted: () => _toggle(id, name),
                deleteIconColor: theme.colorScheme.onSurfaceVariant,
              );
            }).toList(),
          ),
          const SizedBox(height: 8),
        ],
        TextField(
          controller: _controller,
          decoration: InputDecoration(
            hintText: 'search by name or phone…',
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
        if (_results.isNotEmpty) ...[
          const SizedBox(height: 4),
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: theme.colorScheme.outlineVariant),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: _results.map((r) {
                final isSelected = selected.contains(r.id);
                return ListTile(
                  dense: true,
                  title: Text(
                    r.displayName,
                    style: const TextStyle(fontSize: 13),
                  ),
                  subtitle: Text(
                    r.phone,
                    style: TextStyle(
                      fontSize: 12,
                      color: theme.colorScheme.onSurfaceVariant,
                    ),
                  ),
                  trailing: null,
                  onTap: () {
                    _toggle(r.id, r.displayName);
                    if (!isSelected) {
                      _controller.clear();
                      setState(() => _results = []);
                    }
                  },
                );
              }).toList(),
            ),
          ),
        ],
      ],
    );
  }
}
