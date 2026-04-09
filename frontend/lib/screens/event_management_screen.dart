import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/event_management_row.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/create_datetime_poll.dart';
import 'package:pda/utils/snackbar.dart';
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
          final filtered = myEventsOnly && user != null
              ? events
                    .where(
                      (e) =>
                          e.createdById == user.id ||
                          e.coHostIds.contains(user.id),
                    )
                    .toList()
              : events;
          return _EventManagementBody(
            events: filtered,
            myEventsOnly: myEventsOnly,
          );
        },
      ),
    );
  }
}

enum _SortField { date, title, type }

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

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  List<Event> _filterAndSort(List<Event> events) {
    var filtered = events;
    if (_query.isNotEmpty) {
      final q = _query.toLowerCase();
      filtered = events
          .where((e) => e.title.toLowerCase().contains(q))
          .toList();
    }
    filtered = List.of(filtered);
    filtered.sort((a, b) {
      return switch (_sort) {
        _SortField.date => b.startDatetime.compareTo(a.startDatetime),
        _SortField.title => a.title.toLowerCase().compareTo(
          b.title.toLowerCase(),
        ),
        _SortField.type => a.eventType.compareTo(b.eventType),
      };
    });
    return filtered;
  }

  Future<void> _showCreateDialog() async {
    final result = await showEventForm(context);
    if (result == null) return;
    try {
      final api = ref.read(apiClientProvider);
      final response = await api.post(
        '/api/community/events/',
        data: result.data,
      );
      final eventId = (response.data as Map<String, dynamic>)['id'] as String;
      if (result.photo != null) {
        await uploadEventPhoto(ref, eventId, result.photo!);
      }
      if (result.datetimePollOptions.isNotEmpty) {
        await createDatetimePoll(
          ref: ref,
          eventId: eventId,
          eventTitle: result.data['title'] as String,
          options: result.datetimePollOptions,
        );
      }
      ref.invalidate(eventsProvider);
      if (mounted) {
        showSnackBar(context, 'event created 🌱');
        context.push('/events/$eventId');
      }
    } catch (e) {
      if (mounted) {
        showErrorSnackBar(context, ApiError.from(e).message);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final filtered = _filterAndSort(widget.events);

    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(24, 16, 24, 12),
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
        Expanded(
          child: filtered.isEmpty
              ? Center(
                  child: Padding(
                    padding: const EdgeInsets.all(32),
                    child: Column(
                      mainAxisAlignment: MainAxisAlignment.center,
                      children: [
                        const Icon(
                          Icons.calendar_today_outlined,
                          size: 64,
                          color: Colors.grey,
                        ),
                        const SizedBox(height: 16),
                        Text(
                          _query.isNotEmpty
                              ? 'no matches for "$_query"'
                              : 'no events yet',
                          style: const TextStyle(
                            fontSize: 18,
                            color: Colors.grey,
                          ),
                        ),
                        if (_query.isEmpty) ...[
                          const SizedBox(height: 8),
                          Text(
                            widget.myEventsOnly
                                ? "you haven't created or co-hosted any events yet"
                                : 'create one to get started',
                            style: const TextStyle(color: Colors.grey),
                          ),
                        ],
                      ],
                    ),
                  ),
                )
              : ListView.separated(
                  padding: const EdgeInsets.fromLTRB(24, 0, 24, 24),
                  itemCount: filtered.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 12),
                  itemBuilder: (context, index) =>
                      EventManagementRow(event: filtered[index]),
                ),
        ),
      ],
    );
  }
}
