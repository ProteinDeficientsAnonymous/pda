import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:logging/logging.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/calendar/event_form_dialog.dart';
import 'package:pda/screens/guest_add_event_dialog.dart';
import 'package:pda/utils/snackbar.dart';
import 'package:pda/utils/submit_event.dart';
import 'package:pda/widgets/app_scaffold.dart';

final _log = Logger('AddEventScreen');

class AddEventScreen extends ConsumerStatefulWidget {
  const AddEventScreen({super.key});

  @override
  ConsumerState<AddEventScreen> createState() => _AddEventScreenState();
}

class _AddEventScreenState extends ConsumerState<AddEventScreen> {
  @override
  void initState() {
    super.initState();
    WidgetsBinding.instance.addPostFrameCallback((_) => _launch());
  }

  Future<void> _launch() async {
    if (!mounted) return;

    final user = ref.read(authProvider).value;
    if (user == null) {
      if (!mounted) return;
      final loggedIn = await showDialog<bool>(
        context: context,
        builder: (_) => const GuestAddEventDialog(),
      );
      if (!mounted) return;
      if (loggedIn != true) {
        context.go('/calendar');
        return;
      }
    }

    if (!mounted) return;
    final result = await Navigator.of(context).push<EventFormResult>(
      MaterialPageRoute(
        fullscreenDialog: true,
        builder: (_) => const EventFormDialog(fullScreen: true),
      ),
    );

    if (!mounted) return;
    if (result == null) {
      context.go('/calendar');
      return;
    }

    try {
      final eventId = await submitNewEvent(ref, result);
      if (!mounted) return;
      final isDraft = result.status == 'draft';
      showSnackBar(context, isDraft ? 'draft saved' : 'event created 🌱');
      context.go('/events/$eventId');
    } catch (e, st) {
      _log.warning('failed to create event', e, st);
      if (!mounted) return;
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(
          content: Text('something went wrong creating that event'),
        ),
      );
      context.go('/calendar');
    }
  }

  @override
  Widget build(BuildContext context) {
    return const AppScaffold(
      maxWidth: 800,
      child: Center(child: CircularProgressIndicator()),
    );
  }
}
