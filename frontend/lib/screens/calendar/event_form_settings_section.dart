import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/calendar/co_host_picker.dart';

class EventFormSettingsSection extends ConsumerWidget {
  final bool rsvpEnabled;
  final String visibility;
  final String eventType;
  final String partifulLinkText;
  final String invitePermission;
  final Set<String> coHostIds;
  final Map<String, String> coHostNames;
  final Set<String> invitedUserIds;
  final Map<String, String> invitedUserNames;
  final ScrollController scrollController;
  final bool allowPlusOnes;
  final ValueChanged<bool> onRsvpChanged;
  final ValueChanged<bool> onAllowPlusOnesChanged;
  final ValueChanged<String> onVisibilityChanged;
  final ValueChanged<bool> onOfficialChanged;
  final ValueChanged<String> onInvitePermissionChanged;
  final ValueChanged<Set<String>> onCoHostsChanged;
  final ValueChanged<Set<String>> onInvitedChanged;

  const EventFormSettingsSection({
    super.key,
    required this.rsvpEnabled,
    required this.allowPlusOnes,
    required this.visibility,
    required this.eventType,
    required this.partifulLinkText,
    required this.invitePermission,
    required this.coHostIds,
    required this.coHostNames,
    required this.invitedUserIds,
    required this.invitedUserNames,
    required this.scrollController,
    required this.onRsvpChanged,
    required this.onAllowPlusOnesChanged,
    required this.onVisibilityChanged,
    required this.onOfficialChanged,
    required this.onInvitePermissionChanged,
    required this.onCoHostsChanged,
    required this.onInvitedChanged,
  });

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final theme = Theme.of(context);
    final canTagOfficial =
        ref
            .watch(authProvider)
            .value
            ?.hasPermission(Permission.tagOfficialEvent) ??
        false;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Divider(),
        const SizedBox(height: 8),
        SwitchListTile(
          value: rsvpEnabled,
          onChanged: onRsvpChanged,
          title: const Text('enable RSVPs'),
          subtitle: rsvpEnabled && partifulLinkText.trim().isNotEmpty
              ? Text(
                  'you have a partiful link set — consider using one or the other',
                  style: TextStyle(color: theme.colorScheme.tertiary),
                )
              : null,
          contentPadding: EdgeInsets.zero,
        ),
        if (rsvpEnabled) ...[
          SwitchListTile(
            value: allowPlusOnes,
            onChanged: onAllowPlusOnesChanged,
            title: const Text('allow +1s'),
            subtitle: const Text('guests can bring additional people'),
            contentPadding: EdgeInsets.zero,
          ),
        ],
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: visibility,
          decoration: const InputDecoration(labelText: 'visibility'),
          items: const [
            DropdownMenuItem(
              value: PageVisibility.public_,
              child: Text('public'),
            ),
            DropdownMenuItem(
              value: PageVisibility.membersOnly,
              child: Text('members only'),
            ),
            DropdownMenuItem(
              value: PageVisibility.inviteOnly,
              child: Text('invite only'),
            ),
          ],
          onChanged: (val) =>
              onVisibilityChanged(val ?? PageVisibility.public_),
        ),
        if (canTagOfficial) ...[
          const SizedBox(height: 8),
          SwitchListTile(
            title: const Text('official PDA event'),
            subtitle: const Text('mark as an official PDA-organized event'),
            value: eventType == EventType.official,
            contentPadding: EdgeInsets.zero,
            onChanged: onOfficialChanged,
          ),
        ],
        const SizedBox(height: 16),
        const Divider(),
        const SizedBox(height: 8),
        Text('co-hosts', style: theme.textTheme.labelLarge),
        const SizedBox(height: 8),
        CoHostPicker(
          selectedIds: coHostIds,
          selectedNames: coHostNames,
          onChanged: onCoHostsChanged,
          scrollController: scrollController,
        ),
        const SizedBox(height: 8),
        const Divider(),
        const SizedBox(height: 8),
        DropdownButtonFormField<String>(
          initialValue: invitePermission,
          decoration: const InputDecoration(labelText: 'who can invite?'),
          items: const [
            DropdownMenuItem(
              value: InvitePermission.allMembers,
              child: Text('all members'),
            ),
            DropdownMenuItem(
              value: InvitePermission.coHostsOnly,
              child: Text('co-hosts only'),
            ),
          ],
          onChanged: (val) =>
              onInvitePermissionChanged(val ?? InvitePermission.allMembers),
        ),
        const SizedBox(height: 8),
        Text('invite members', style: theme.textTheme.labelLarge),
        const SizedBox(height: 4),
        Text(
          visibility == PageVisibility.inviteOnly
              ? 'only invited members (plus you and co-hosts) will see this event'
              : 'invited list is only visible to you and co-hosts',
          style: TextStyle(
            fontSize: 12,
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 8),
        CoHostPicker(
          selectedIds: invitedUserIds,
          selectedNames: invitedUserNames,
          onChanged: onInvitedChanged,
          scrollController: scrollController,
        ),
      ],
    );
  }
}
