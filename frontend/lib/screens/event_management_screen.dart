import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/event_management_row.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/submit_event.dart';
import 'package:pda/widgets/app_scaffold.dart';

class EventManagementScreen extends ConsumerWidget {
  final bool myEventsOnly;

  const EventManagementScreen({super.key, this.myEventsOnly = false});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventsAsync = ref.watch(eventsProvider);
    final user = ref.watch(authProvider).value;

    return AppScaffold(
      child: eventsAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) =>
            const Center(child: Text('couldn\'t load events — try refreshing')),
        data: (events) {
          final myEvents = myEventsOnly && user != null
              ? events
                    .where(
                      (e) =>
                          e.createdById == user.id ||
                          e.coHostIds.contains(user.id),
                    )
                    .toList()
              : events;
          return _EventManagementBody(
            events: myEvents,
            myEventsOnly: myEventsOnly,
          );
        },
      ),
    );
  }
}

enum _SortField { date, title, type }

enum _EventFilter { upcoming, past, drafts, cancelled }

class _EventManagementBody extends ConsumerStatefulWidget {
  final List<Event> events;
  final bool myEventsOnly;

  const _EventManagementBody({
    required this.events,
    required this.myEventsOnly,
  });

  @override
  ConsumerState<_EventManagementBody> createState() =>
      _EventManagementBodyState();
}

class _EventManagementBodyState extends ConsumerState<_EventManagementBody> {
  final _searchController = TextEditingController();
  String _query = '';
  _SortField _sort = _SortField.date;
  _EventFilter _filter = _EventFilter.upcoming;

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Event> _applyTabFilter(List<Event> events) {
    return switch (_filter) {
      _EventFilter.upcoming => events.where((e) => !e.isPast).toList(),
      _EventFilter.past => events.where((e) => e.isPast).toList(),
      _EventFilter.drafts => [],
      _EventFilter.cancelled => [],
    };
  }

  Future<void> _showCreateDialog() async {
    final result = await showEventForm(context);
    if (result == null) return;
    try {
      final eventId = await submitNewEvent(ref, result);
      if (mounted) {
        final isDraft = result.status == 'draft';
        showSnackBar(context, isDraft ? 'draft saved' : 'event created 🌱');
        context.push('/events/$eventId');
      }
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  List<Event> _searchFilter(List<Event> events) {
    if (_query.isEmpty) return events;
    final q = _query.toLowerCase();
    return events.where((e) => e.title.toLowerCase().contains(q)).toList();
  }

  List<Event> _applySortOrder(List<Event> events) {
    final result = List.of(events);
    result.sort((a, b) {
      return switch (_sort) {
        _SortField.date => b.startDatetime.compareTo(a.startDatetime),
        _SortField.title => a.title.toLowerCase().compareTo(
          b.title.toLowerCase(),
        ),
        _SortField.type => a.eventType.compareTo(b.eventType),
      };
    });
    return result;
  }

  String _emptyMessage() {
    if (_query.isNotEmpty) return 'no matches for "$_query"';
    return switch (_filter) {
      _EventFilter.upcoming => 'no upcoming events',
      _EventFilter.past => 'no past events',
      _EventFilter.drafts => 'no drafts yet 🌿',
      _EventFilter.cancelled => 'no cancelled events',
    };
  }

  String _emptySubtext() {
    if (_query.isNotEmpty || !widget.myEventsOnly) {
      return 'create one to get started';
    }
    return switch (_filter) {
      _EventFilter.upcoming =>
        "you haven't created or co-hosted any upcoming events",
      _EventFilter.past => "you haven't created or co-hosted any past events",
      _EventFilter.drafts =>
        'hit save draft when you want to finish an event later',
      _EventFilter.cancelled => 'none of your events have been cancelled',
    };
  }

  Widget _buildList(List<Event> events) {
    final filtered = _applySortOrder(_searchFilter(events));
    if (filtered.isEmpty) {
      return Center(
        child: Padding(
          padding: const EdgeInsets.all(32),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Icon(
                Icons.calendar_today_outlined,
                size: 64,
                color: Theme.of(context).colorScheme.onSurfaceVariant,
              ),
              const SizedBox(height: 16),
              Text(
                _emptyMessage(),
                style: TextStyle(
                  fontSize: 18,
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 8),
              Text(
                _emptySubtext(),
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
            ],
          ),
        ),
      );
    }
    return ListView.separated(
      padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
      itemCount: filtered.length,
      separatorBuilder: (_, __) => const SizedBox(height: 12),
      itemBuilder: (context, index) =>
          EventManagementRow(event: filtered[index]),
    );
  }

  Widget _buildDraftsTab() {
    final draftsAsync = ref.watch(draftEventsProvider);
    return draftsAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) =>
          const Center(child: Text("couldn't load drafts — try refreshing")),
      data: _buildList,
    );
  }

  Widget _buildCancelledTab() {
    final cancelledAsync = ref.watch(cancelledEventsProvider);
    return cancelledAsync.when(
      loading: () => const Center(child: CircularProgressIndicator()),
      error: (_, __) => const Center(
        child: Text("couldn't load cancelled events — try refreshing"),
      ),
      data: _buildList,
    );
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 0),
          child: Row(
            children: [
              Expanded(
                child: TextField(
                  controller: _searchController,
                  decoration: InputDecoration(
                    hintText: 'search events...',
                    prefixIcon: const Icon(Icons.search, size: 20),
                    isDense: true,
                    border: OutlineInputBorder(
                      borderRadius: BorderRadius.circular(8),
                    ),
                    contentPadding: const EdgeInsets.symmetric(
                      horizontal: 12,
                      vertical: 10,
                    ),
                    suffixIcon: _query.isNotEmpty
                        ? IconButton(
                            icon: const Icon(Icons.close, size: 18),
                            onPressed: () {
                              _searchController.clear();
                              setState(() => _query = '');
                            },
                          )
                        : null,
                  ),
                  maxLength: 100,
                  buildCounter:
                      (
                        _, {
                        required currentLength,
                        required isFocused,
                        maxLength,
                      }) => null,
                  onChanged: (v) => setState(() => _query = v),
                ),
              ),
              const SizedBox(width: 8),
              SegmentedButton<_SortField>(
                segments: const [
                  ButtonSegment(value: _SortField.date, label: Text('date')),
                  ButtonSegment(value: _SortField.title, label: Text('title')),
                  ButtonSegment(value: _SortField.type, label: Text('type')),
                ],
                selected: {_sort},
                onSelectionChanged: (s) => setState(() => _sort = s.first),
                showSelectedIcon: false,
                style: ButtonStyle(
                  visualDensity: VisualDensity.compact,
                  textStyle: WidgetStatePropertyAll(
                    Theme.of(context).textTheme.labelSmall,
                  ),
                ),
              ),
              const SizedBox(width: 8),
              FilledButton.icon(
                onPressed: _showCreateDialog,
                icon: const Icon(Icons.add_circle_outline),
                label: const Text('new event'),
              ),
            ],
          ),
        ),
        if (widget.myEventsOnly) ...[
          const SizedBox(height: 12),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 24),
            child: SegmentedButton<_EventFilter>(
              segments: const [
                ButtonSegment(
                  value: _EventFilter.upcoming,
                  label: Text('upcoming'),
                ),
                ButtonSegment(value: _EventFilter.past, label: Text('past')),
                ButtonSegment(
                  value: _EventFilter.drafts,
                  label: Text('drafts'),
                ),
                ButtonSegment(
                  value: _EventFilter.cancelled,
                  label: Text('cancelled'),
                ),
              ],
              selected: {_filter},
              onSelectionChanged: (s) => setState(() => _filter = s.first),
              showSelectedIcon: false,
              style: ButtonStyle(
                visualDensity: VisualDensity.compact,
                textStyle: WidgetStatePropertyAll(
                  Theme.of(context).textTheme.labelSmall,
                ),
              ),
            ),
          ),
        ],
        const SizedBox(height: 12),
        Expanded(
          child: switch (_filter) {
            _EventFilter.drafts when widget.myEventsOnly => _buildDraftsTab(),
            _EventFilter.cancelled when widget.myEventsOnly =>
              _buildCancelledTab(),
            _ => _buildList(_applyTabFilter(widget.events)),
          },
        ),
      ],
    );
  }
}
