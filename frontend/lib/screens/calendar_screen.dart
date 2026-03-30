import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/day_view.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/screens/calendar/month_view.dart';
import 'package:pda/screens/calendar/week_view.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/widgets/app_scaffold.dart';
import 'package:pda/widgets/phone_form_field.dart';

enum _CalendarView { month, week, day }

class CalendarScreen extends ConsumerStatefulWidget {
  const CalendarScreen({super.key});

  @override
  ConsumerState<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends ConsumerState<CalendarScreen> {
  _CalendarView _view = _CalendarView.month;
  late DateTime _selectedDate;

  @override
  void initState() {
    super.initState();
    final now = DateTime.now();
    _selectedDate = DateTime(now.year, now.month, now.day);
  }

  void _onDateChanged(DateTime date) {
    setState(() => _selectedDate = date);
  }

  void _onViewChanged(_CalendarView view) {
    setState(() => _view = view);
  }

  void _goToToday() {
    final now = DateTime.now();
    setState(() => _selectedDate = DateTime(now.year, now.month, now.day));
  }

  Future<void> _openCreateEvent() async {
    final user = ref.read(authProvider).valueOrNull;

    if (user == null) {
      if (!mounted) return;
      final loggedIn = await showDialog<bool>(
        context: context,
        builder: (_) => const _GuestAddEventDialog(),
      );
      if (loggedIn != true || !mounted) return;
    }

    final result = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (_) => const EventFormDialog(),
    );
    if (result == null) return;

    try {
      final api = ref.read(apiClientProvider);
      await api.post('/api/community/events/', data: result);
      ref.invalidate(eventsProvider);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          const SnackBar(
            content: Text('something went wrong creating that event'),
          ),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final eventsAsync = ref.watch(eventsProvider);
    // Rebuild when auth changes (FAB tap checks auth) and re-fetch events
    // so authenticated users see member-only fields (location, links, RSVP).
    ref.listen(authProvider, (_, __) => ref.invalidate(eventsProvider));

    return AppScaffold(
      child: Column(
        children: [
          _CalendarToolbar(
            selected: _view,
            onSelected: _onViewChanged,
            onToday: _goToToday,
          ),
          Expanded(
            child: eventsAsync.when(
              loading: () => const Center(child: CircularProgressIndicator()),
              error:
                  (e, _) => const Center(
                    child: Text('couldn\'t load events — try refreshing'),
                  ),
              data: (events) => _buildView(events),
            ),
          ),
          Padding(
            padding: const EdgeInsets.only(bottom: 16, top: 8),
            child: FloatingActionButton.extended(
              onPressed: _openCreateEvent,
              icon: const Icon(Icons.add_circle_outline),
              label: const Text('add event'),
            ),
          ),
        ],
      ),
    );
  }

  Widget _buildView(events) {
    switch (_view) {
      case _CalendarView.month:
        return MonthView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
          onDayTapped: (date) {
            setState(() {
              _selectedDate = date;
              _view = _CalendarView.day;
            });
          },
        );
      case _CalendarView.week:
        return WeekView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
          onDayTapped: (date) {
            setState(() {
              _selectedDate = date;
              _view = _CalendarView.day;
            });
          },
        );
      case _CalendarView.day:
        return DayView(
          events: events,
          selectedDate: _selectedDate,
          onDateChanged: _onDateChanged,
        );
    }
  }
}

class _CalendarToolbar extends StatelessWidget {
  final _CalendarView selected;
  final ValueChanged<_CalendarView> onSelected;
  final VoidCallback onToday;

  const _CalendarToolbar({
    required this.selected,
    required this.onSelected,
    required this.onToday,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          SegmentedButton<_CalendarView>(
            segments: const [
              ButtonSegment(value: _CalendarView.month, label: Text('month')),
              ButtonSegment(value: _CalendarView.week, label: Text('week')),
              ButtonSegment(value: _CalendarView.day, label: Text('day')),
            ],
            selected: {selected},
            onSelectionChanged: (s) => onSelected(s.first),
          ),
          const SizedBox(height: 6),
          OutlinedButton(onPressed: onToday, child: const Text('today')),
        ],
      ),
    );
  }
}

// ---------------------------------------------------------------------------
// Guest "add event" dialog — shown when an unauthenticated user taps the FAB.
// Walks through: phone check → login (if member) or join redirect (if not).
// ---------------------------------------------------------------------------

enum _GuestStep { phone, password }

class _GuestAddEventDialog extends ConsumerStatefulWidget {
  const _GuestAddEventDialog();

  @override
  ConsumerState<_GuestAddEventDialog> createState() =>
      _GuestAddEventDialogState();
}

class _GuestAddEventDialogState extends ConsumerState<_GuestAddEventDialog> {
  final _formKey = GlobalKey<FormState>();
  final _passwordController = TextEditingController();
  String _phoneNumber = '';
  _GuestStep _step = _GuestStep.phone;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _passwordController.dispose();
    super.dispose();
  }

  Future<void> _checkPhone() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final resp = await api.post(
        '/api/community/check-phone/',
        data: {'phone_number': _phoneNumber},
      );
      final exists = (resp.data as Map<String, dynamic>)['exists'] as bool;
      if (!mounted) return;
      if (exists) {
        setState(() {
          _step = _GuestStep.password;
          _loading = false;
        });
      } else {
        Navigator.of(context).pop();
        context.go('/join');
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = ApiError.from(e).message;
          _loading = false;
        });
      }
    }
  }

  Future<void> _login() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .login(_phoneNumber, _passwordController.text);
      if (!mounted) return;
      final authState = ref.read(authProvider);
      if (authState.hasError) {
        setState(() {
          _error = ApiError.from(authState.error!).message;
          _loading = false;
        });
        return;
      }
      // Logged in — signal success to caller, which will open the event form.
      Navigator.of(context).pop(true);
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = ApiError.from(e).message;
          _loading = false;
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final isPhone = _step == _GuestStep.phone;

    return AlertDialog(
      title: const Text('add an event'),
      content: SizedBox(
        width: 360,
        child: Form(
          key: _formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                isPhone
                    ? 'you need to be logged in to add events — pop in your number and we\'ll sort you out'
                    : 'welcome back! enter your password to get in',
                style: TextStyle(
                  color: Theme.of(context).colorScheme.onSurfaceVariant,
                ),
              ),
              const SizedBox(height: 20),
              if (isPhone)
                PhoneFormField(
                  onChanged: (v) => setState(() => _phoneNumber = v),
                  helperText:
                      'not a member yet? we\'ll send you to the join form',
                  textInputAction: TextInputAction.done,
                  onFieldSubmitted: (_) => _loading ? null : _checkPhone(),
                )
              else
                TextFormField(
                  controller: _passwordController,
                  decoration: const InputDecoration(
                    labelText: 'Password',
                    border: OutlineInputBorder(),
                  ),
                  obscureText: true,
                  autofillHints: const [AutofillHints.password],
                  validator:
                      (v) => (v == null || v.isEmpty) ? 'Required' : null,
                  onFieldSubmitted: (_) => _loading ? null : _login(),
                ),
              if (_error != null) ...[
                const SizedBox(height: 12),
                Text(
                  _error!,
                  style: TextStyle(
                    color: Theme.of(context).colorScheme.error,
                    fontSize: 13,
                  ),
                ),
              ],
            ],
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('cancel'),
        ),
        if (_step == _GuestStep.password)
          TextButton(
            onPressed:
                _loading
                    ? null
                    : () => setState(() {
                      _step = _GuestStep.phone;
                      _error = null;
                    }),
            child: const Text('back'),
          ),
        FilledButton(
          onPressed: _loading ? null : (isPhone ? _checkPhone : _login),
          child:
              _loading
                  ? const SizedBox(
                    width: 16,
                    height: 16,
                    child: CircularProgressIndicator(strokeWidth: 2),
                  )
                  : Text(isPhone ? 'continue' : 'log in'),
        ),
      ],
    );
  }
}
