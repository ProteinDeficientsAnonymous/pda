import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/providers/event_provider.dart';
import 'package:pda/screens/calendar/event_detail_panel.dart';
import 'package:pda/services/api_error.dart';
import 'package:pda/widgets/app_scaffold.dart';

class EventDetailScreen extends ConsumerWidget {
  final String eventId;

  const EventDetailScreen({super.key, required this.eventId});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final eventAsync = ref.watch(eventDetailProvider(eventId));

    return AppScaffold(
      maxWidth: 800,
      child: eventAsync.when(
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (e, _) {
          final apiError = ApiError.from(e);
          final message = switch (apiError) {
            ForbiddenError() => 'this event is invite only',
            NotFoundError() => 'event not found',
            _ => 'couldn\'t load event — try refreshing',
          };
          return Center(child: Text(message));
        },
        data: (event) => EventDetailContent(
          event: event,
          fullPage: true,
          onDeleted: () =>
              context.canPop() ? context.pop() : context.go('/events/mine'),
        ),
      ),
    );
  }
}
