import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/models/event.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/utils/launcher.dart';
import 'package:pda/screens/calendar/event_detail_widgets.dart';
import 'package:pda/screens/calendar/event_login_gate.dart';
import 'rsvp_section.dart';
import 'invite_modal.dart';

class EventSectionCard extends StatelessWidget {
  final String label;
  final Widget child;

  const EventSectionCard({super.key, required this.label, required this.child});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      width: double.infinity,
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHighest.withValues(alpha: 0.3),
        borderRadius: BorderRadius.circular(14),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            label,
            style: Theme.of(context).textTheme.labelMedium?.copyWith(
              color: cs.onSurfaceVariant,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),
          child,
        ],
      ),
    );
  }
}

/// Shows member-only content (location, links, RSVP, admin actions) or a
/// login/join prompt for unauthenticated visitors.
class EventMemberSection extends ConsumerWidget {
  final Event event;
  final String location;

  const EventMemberSection({
    super.key,
    required this.event,
    required this.location,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = ref.watch(authProvider).value;
    if (user != null) {
      // Build host list: creator first (no photo), then co-hosts (with photos)
      final hosts = <({String id, String name, String photoUrl})>[];
      if (event.createdByName != null) {
        hosts.add((
          id: event.createdById ?? '',
          name: event.createdByName!,
          photoUrl: '',
        ));
      }
      for (var i = 0; i < event.coHostNames.length; i++) {
        hosts.add((
          id: i < event.coHostIds.length ? event.coHostIds[i] : '',
          name: event.coHostNames[i],
          photoUrl: i < event.coHostPhotoUrls.length
              ? event.coHostPhotoUrls[i]
              : '',
        ));
      }

      final isCoHost =
          user.id == event.createdById || event.coHostIds.contains(user.id);

      final detailRows = <Widget>[
        if (location.isNotEmpty)
          Semantics(
            button: true,
            label: 'Open $location in maps',
            child: InkWell(
              onTap: () => openLocationInMaps(location),
              borderRadius: BorderRadius.circular(4),
              child: EventDetailRow(
                icon: Icons.location_on_outlined,
                text: location.split(', ').first,
                color: Theme.of(context).colorScheme.primary,
              ),
            ),
          ),
        if (event.whatsappLink.isNotEmpty)
          EventLinkRow(
            icon: Icons.chat_bubble_outline,
            label: 'WhatsApp group',
            url: event.whatsappLink,
          ),
        if (event.partifulLink.isNotEmpty)
          EventLinkRow(
            icon: Icons.celebration,
            label: 'Partiful',
            url: event.partifulLink,
          ),
        if (event.otherLink.isNotEmpty)
          EventLinkRow(
            icon: Icons.link_outlined,
            label: event.otherLink,
            url: event.otherLink,
          ),
        if (event.price.isNotEmpty)
          EventDetailRow(icon: Icons.attach_money, text: event.price),
        if (event.venmoLink.isNotEmpty)
          EventLinkRow(
            icon: Icons.payment,
            label: 'venmo',
            url: event.venmoLink,
          ),
        if (event.cashappLink.isNotEmpty)
          EventLinkRow(
            icon: Icons.monetization_on_outlined,
            label: 'cash app',
            url: event.cashappLink,
          ),
        if (event.zelleInfo.isNotEmpty)
          EventDetailRow(
            icon: Icons.account_balance_outlined,
            text: 'zelle: ${event.zelleInfo}',
          ),
        ...event.surveySlugs
            .where((slug) => slug != event.datetimePollSlug)
            .map(
              (slug) => InkWell(
                onTap: () => context.go('/surveys/$slug'),
                borderRadius: BorderRadius.circular(8),
                child: Padding(
                  padding: const EdgeInsets.symmetric(vertical: 4),
                  child: Row(
                    children: [
                      Icon(
                        Icons.rate_review_rounded,
                        size: 18,
                        color: Theme.of(context).colorScheme.primary,
                      ),
                      const SizedBox(width: 8),
                      Text(
                        'give feedback',
                        style: TextStyle(
                          color: Theme.of(context).colorScheme.primary,
                          fontWeight: FontWeight.w500,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ),
      ];

      return Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (hosts.isNotEmpty)
            EventSectionCard(
              label: hosts.length > 1
                  ? EventDetailLabel.coHosts
                  : EventDetailLabel.host,
              child: Wrap(
                spacing: 12,
                runSpacing: 8,
                children: [
                  for (final host in hosts) EventDetailHostChip(host: host),
                ],
              ),
            ),
          if (detailRows.isNotEmpty) ...[
            const SizedBox(height: 12),
            EventSectionCard(
              label: EventDetailLabel.details,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  for (var i = 0; i < detailRows.length; i++) ...[
                    detailRows[i],
                    if (i < detailRows.length - 1) const SizedBox(height: 8),
                  ],
                ],
              ),
            ),
          ],
          if (isCoHost) ...[
            const SizedBox(height: 12),
            FilledButton.tonalIcon(
              icon: const Icon(Icons.person_add_alt_1_outlined, size: 18),
              label: const Text('invite friends'),
              onPressed: () => showDialog(
                context: context,
                builder: (_) => InviteModal(event: event),
              ),
            ),
          ],
          if (event.rsvpEnabled) ...[
            const SizedBox(height: 12),
            EventSectionCard(
              label: EventDetailLabel.rsvp,
              child: RSVPSection(event: event),
            ),
          ],
          const SizedBox(height: 12),
          EventAdminActions(event: event),
        ],
      );
    }
    return LoginOrJoinSection(event: event);
  }
}
