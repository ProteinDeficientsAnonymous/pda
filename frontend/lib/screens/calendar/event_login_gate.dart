import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_action_dialogs.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/utils/create_datetime_poll.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/widgets/loading_button.dart';
import 'package:pda/widgets/phone_form_field.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/screens/calendar/event_form_dialog.dart';

final _log = Logger('EventLoginGate');

/// Shows admin action buttons (edit / cancel / delete / uncancel) for users
/// who have permission to manage the event.
class EventAdminActions extends ConsumerStatefulWidget {
  final Event event;

  /// Called after the event is **deleted** (soft-deleted). The caller should
  /// navigate away since the event is no longer accessible.
  final VoidCallback? onDeleted;

  const EventAdminActions({super.key, required this.event, this.onDeleted});

  @override
  ConsumerState<EventAdminActions> createState() => _EventAdminActionsState();
}

class _EventAdminActionsState extends ConsumerState<EventAdminActions> {
  bool _loading = false;

  bool get _hasAttendees =>
      widget.event.invitedCount > 0 || widget.event.attendingCount > 0;

  Future<void> _cancel() async {
    final result = await showCancelEventDialog(context, widget.event);
    if (!result.confirmed) return;

    setState(() => _loading = true);
    try {
      await patchEventStatus(
        ref,
        widget.event.id,
        status: EventStatus.cancelled,
        notifyAttendees: result.notifyAttendees,
      );
      _log.info('cancelled event ${widget.event.id}');
      if (mounted) showSnackBar(context, 'event cancelled');
      // Stay on page — cancelled chip renders via invalidated provider
    } catch (e, st) {
      _log.warning('failed to cancel event', e, st);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _delete() async {
    final confirmed = await showDeleteEventDialog(context, widget.event);
    if (!confirmed) return;

    setState(() => _loading = true);
    try {
      await patchEventStatus(ref, widget.event.id, status: EventStatus.deleted);
      _log.info('deleted event ${widget.event.id}');
      if (mounted) {
        showSnackBar(context, 'event deleted');
        widget.onDeleted?.call();
      }
    } catch (e, st) {
      _log.warning('failed to delete event', e, st);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _uncancel() async {
    setState(() => _loading = true);
    try {
      await patchEventStatus(ref, widget.event.id, status: EventStatus.active);
      _log.info('uncancelled event ${widget.event.id}');
      if (mounted) showSnackBar(context, 'event reinstated');
    } catch (e, st) {
      _log.warning('failed to uncancel event', e, st);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _edit() async {
    final result = await showEventForm(context, event: widget.event);
    if (result == null) return;

    setState(() => _loading = true);
    try {
      final api = ref.read(apiClientProvider);
      await api.patch(
        '/api/community/events/${widget.event.id}/',
        data: result.data,
      );
      if (result.photo != null) {
        await uploadEventPhoto(
          ref,
          widget.event.id,
          result.photo!,
          oldPhotoUrl: widget.event.photoUrl,
        );
      } else if (result.removePhoto) {
        await deleteEventPhoto(ref, widget.event.id);
      }
      if (result.datetimePollOptions.isNotEmpty) {
        await createDatetimePoll(
          ref: ref,
          eventId: widget.event.id,
          eventTitle: result.data['title'] as String,
          options: result.datetimePollOptions,
        );
      }
      ref.invalidate(eventsProvider);
      ref.invalidate(eventDetailProvider(widget.event.id));
      _log.info('edited event ${widget.event.id}');
    } catch (e, st) {
      _log.warning('failed to edit event', e, st);
      if (mounted) showErrorSnackBar(context, ApiError.from(e).message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    if (_loading) {
      return const Center(child: CircularProgressIndicator());
    }

    final user = ref.watch(authProvider).value;
    if (user == null) return const SizedBox.shrink();

    final isCreator = widget.event.createdById == user.id;
    final isManager = user.hasPermission(Permission.manageEvents);
    final isCoHost = widget.event.coHostIds.contains(user.id);
    final canEdit = isCreator || isManager || isCoHost;
    if (!canEdit) return const SizedBox.shrink();

    final isCancelled = widget.event.status == EventStatus.cancelled;

    // Past events: edit + delete only (can't cancel something already done)
    // Upcoming with no attendees: edit + delete only
    // Upcoming with attendees: edit + cancel
    // Cancelled: uncancel (creator/manager only) + delete
    Widget buttons;
    if (isCancelled) {
      buttons = Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (isCreator || isManager) ...[
            OutlinedButton.icon(
              onPressed: _uncancel,
              icon: const Icon(Icons.restore, size: 16),
              label: const Text('uncancel'),
            ),
            const SizedBox(width: 12),
          ],
          OutlinedButton.icon(
            onPressed: _delete,
            icon: Icon(
              Icons.delete_outline,
              size: 16,
              color: Theme.of(context).colorScheme.error,
            ),
            label: Text(
              'delete',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
            style: OutlinedButton.styleFrom(
              side: BorderSide(color: Theme.of(context).colorScheme.error),
            ),
          ),
        ],
      );
    } else if (!widget.event.isPast && _hasAttendees) {
      // Upcoming with attendees — show cancel (delete happens after cancel)
      buttons = Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          OutlinedButton.icon(
            onPressed: _edit,
            icon: const Icon(Icons.edit_outlined, size: 16),
            label: const Text('edit'),
          ),
          const SizedBox(width: 12),
          OutlinedButton.icon(
            onPressed: _cancel,
            icon: Icon(
              Icons.cancel_outlined,
              size: 16,
              color: Theme.of(context).colorScheme.error,
            ),
            label: Text(
              'cancel event',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
            style: OutlinedButton.styleFrom(
              side: BorderSide(color: Theme.of(context).colorScheme.error),
            ),
          ),
        ],
      );
    } else {
      // Past event or upcoming with no attendees — show delete directly
      buttons = Row(
        mainAxisAlignment: MainAxisAlignment.center,
        children: [
          if (!widget.event.isPast) ...[
            OutlinedButton.icon(
              onPressed: _edit,
              icon: const Icon(Icons.edit_outlined, size: 16),
              label: const Text('edit'),
            ),
            const SizedBox(width: 12),
          ],
          OutlinedButton.icon(
            onPressed: _delete,
            icon: Icon(
              Icons.delete_outline,
              size: 16,
              color: Theme.of(context).colorScheme.error,
            ),
            label: Text(
              'delete',
              style: TextStyle(color: Theme.of(context).colorScheme.error),
            ),
            style: OutlinedButton.styleFrom(
              side: BorderSide(color: Theme.of(context).colorScheme.error),
            ),
          ),
        ],
      );
    }

    return buttons;
  }
}

/// Shown to unauthenticated visitors. Collects phone number, checks if they're
/// a member, then either prompts login or prompts them to submit a join request.
class LoginOrJoinSection extends ConsumerStatefulWidget {
  final Event event;

  const LoginOrJoinSection({super.key, required this.event});

  @override
  ConsumerState<LoginOrJoinSection> createState() => _LoginOrJoinSectionState();
}

class _LoginOrJoinSectionState extends ConsumerState<LoginOrJoinSection> {
  String _phoneNumber = '';
  final _passwordCtrl = TextEditingController();
  final _phoneKey = GlobalKey<FormState>();
  final _loginKey = GlobalKey<FormState>();

  // null = phone step, "member" / "pending" / "unknown"
  String? _phoneStatus;
  bool _loading = false;
  String? _error;

  @override
  void dispose() {
    _passwordCtrl.dispose();
    super.dispose();
  }

  Future<void> _checkPhone() async {
    if (!(_phoneKey.currentState?.validate() ?? false)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final api = ref.read(apiClientProvider);
      final res = await api.post(
        '/api/community/check-phone/',
        data: {'phone_number': _phoneNumber},
      );
      final status = (res.data as Map<String, dynamic>)['status'] as String;
      setState(() => _phoneStatus = status);
    } catch (e, st) {
      _log.warning('failed to check phone', e, st);
      setState(() => _error = 'something went wrong — try again');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _login() async {
    if (!(_loginKey.currentState?.validate() ?? false)) return;
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      await ref
          .read(authProvider.notifier)
          .login(_phoneNumber, _passwordCtrl.text);
    } catch (e, st) {
      _log.warning('inline login failed', e, st);
      setState(() => _error = 'incorrect password — try again');
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    // Phone step
    if (_phoneStatus == null) {
      return JuicyGate(
        headline: '🔒 log in to see the juicy details',
        subtext:
            'links, RSVPs & more are for members only — enter your number to get in',
        error: _error,
        child: Form(
          key: _phoneKey,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              PhoneFormField(onChanged: (number) => _phoneNumber = number),
              const SizedBox(height: 8),
              LoadingButton(
                label: 'continue',
                onPressed: _checkPhone,
                loading: _loading,
              ),
            ],
          ),
        ),
      );
    }

    // Login step (member found)
    if (_phoneStatus == 'member') {
      return JuicyGate(
        headline: '👋 hey, welcome back!',
        subtext: 'pop in your password and we\'ll get you in',
        error: _error,
        child: Form(
          key: _loginKey,
          child: Column(
            children: [
              TextFormField(
                controller: _passwordCtrl,
                decoration: const InputDecoration(
                  labelText: 'Password',
                  isDense: true,
                ),
                obscureText: true,
                maxLength: 128,
                validator: (v) {
                  if (v == null || v.isEmpty) return 'Required';
                  return null;
                },
                onFieldSubmitted: (_) => _login(),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  LoadingButton(
                    label: 'log in',
                    onPressed: _login,
                    loading: _loading,
                  ),
                  const SizedBox(width: 8),
                  TextButton(
                    onPressed: () => setState(() => _phoneStatus = null),
                    child: const Text('back'),
                  ),
                ],
              ),
            ],
          ),
        ),
      );
    }

    // Request in review
    if (_phoneStatus == 'pending') {
      return JuicyGate(
        headline: '⏳ your request is in review',
        subtext: 'hang tight — we\'ll get back to you soon',
        error: null,
        child: TextButton(
          onPressed: () => setState(() => _phoneStatus = null),
          child: const Text('back'),
        ),
      );
    }

    // Not a member — prompt to join
    return JuicyGate(
      headline: '🌱 not a member yet?',
      subtext: 'request to join the collective and unlock all the good stuff',
      error: null,
      child: Row(
        children: [
          FilledButton(
            onPressed: () => context.push('/join'),
            child: const Text('request to join'),
          ),
          const SizedBox(width: 8),
          TextButton(
            onPressed: () => setState(() => _phoneStatus = null),
            child: const Text('back'),
          ),
        ],
      ),
    );
  }
}

class JuicyGate extends StatelessWidget {
  const JuicyGate({
    super.key,
    required this.headline,
    required this.subtext,
    required this.child,
    required this.error,
  });

  final String headline;
  final String subtext;
  final Widget child;
  final String? error;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Container(
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer.withValues(alpha: 0.4),
        borderRadius: BorderRadius.circular(16),
        border: Border.all(
          color: theme.colorScheme.outline.withValues(alpha: 0.2),
        ),
      ),
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            headline,
            style: theme.textTheme.titleSmall?.copyWith(
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 4),
          Text(
            subtext,
            style: TextStyle(
              fontSize: 13,
              color: theme.colorScheme.onSurfaceVariant,
            ),
          ),
          const SizedBox(height: 12),
          child,
          if (error != null) ...[
            const SizedBox(height: 8),
            Text(
              error!,
              style: TextStyle(fontSize: 13, color: theme.colorScheme.error),
            ),
          ],
        ],
      ),
    );
  }
}
