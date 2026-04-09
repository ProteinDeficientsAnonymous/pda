import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/providers/auth_provider.dart';

class EventFormSettingsSection extends ConsumerWidget {
  final bool rsvpEnabled;
  final String visibilityChoice;
  final String partifulLinkText;
  final String invitePermission;
  final bool allowPlusOnes;
  final ValueChanged<bool> onRsvpChanged;
  final ValueChanged<bool> onAllowPlusOnesChanged;
  final ValueChanged<String> onVisibilityChoiceChanged;
  final ValueChanged<String> onInvitePermissionChanged;

  const EventFormSettingsSection({
    super.key,
    required this.rsvpEnabled,
    required this.allowPlusOnes,
    required this.visibilityChoice,
    required this.partifulLinkText,
    required this.invitePermission,
    required this.onRsvpChanged,
    required this.onAllowPlusOnesChanged,
    required this.onVisibilityChoiceChanged,
    required this.onInvitePermissionChanged,
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
    final showOfficialOption =
        canTagOfficial || visibilityChoice == EventVisibilityChoice.official;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Card(
          margin: EdgeInsets.zero,
          elevation: 0,
          color: theme.colorScheme.surfaceContainerHighest.withValues(
            alpha: 0.4,
          ),
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
          child: Padding(
            padding: const EdgeInsets.all(12),
            child: Column(
              children: [
                _SwitchRow(
                  label: 'enable RSVPs',
                  subtitle: rsvpEnabled && partifulLinkText.trim().isNotEmpty
                      ? Text(
                          'you have a partiful link set — consider using one or the other',
                          style: TextStyle(color: theme.colorScheme.tertiary),
                        )
                      : null,
                  value: rsvpEnabled,
                  onChanged: onRsvpChanged,
                ),
                if (rsvpEnabled) ...[
                  const SizedBox(height: 4),
                  _SwitchRow(
                    label: 'allow +1s',
                    subtitle: const Text(
                      'guests can bring additional people',
                      style: TextStyle(fontSize: 12),
                    ),
                    value: allowPlusOnes,
                    onChanged: onAllowPlusOnesChanged,
                  ),
                  const SizedBox(height: 4),
                  _SwitchRow(
                    label: 'guests can invite friends',
                    value: invitePermission == InvitePermission.allMembers,
                    onChanged: (val) => onInvitePermissionChanged(
                      val
                          ? InvitePermission.allMembers
                          : InvitePermission.coHostsOnly,
                    ),
                  ),
                ],
              ],
            ),
          ),
        ),
        const Divider(height: 40, thickness: 0.5),
        DropdownButtonFormField<String>(
          initialValue: visibilityChoice,
          decoration: const InputDecoration(labelText: 'who can see it'),
          items: [
            if (showOfficialOption)
              const DropdownMenuItem(
                value: EventVisibilityChoice.official,
                child: Text('official PDA event'),
              ),
            const DropdownMenuItem(
              value: EventVisibilityChoice.public_,
              child: Text('public'),
            ),
            const DropdownMenuItem(
              value: EventVisibilityChoice.membersOnly,
              child: Text('pda members only'),
            ),
            const DropdownMenuItem(
              value: EventVisibilityChoice.inviteOnly,
              child: Text('invite only'),
            ),
          ],
          onChanged: (val) =>
              onVisibilityChoiceChanged(val ?? EventVisibilityChoice.public_),
        ),
        const SizedBox(height: 4),
        Text(switch (visibilityChoice) {
          EventVisibilityChoice.official =>
            'this is an official PDA event — visible to everyone',
          EventVisibilityChoice.membersOnly =>
            'only pda members can see this one',
          EventVisibilityChoice.inviteOnly =>
            'invite-only — just the people you pick',
          _ =>
            'anyone can find this event — only pda members get the full details like location and links',
        }, style: TextStyle(fontSize: 12, color: theme.colorScheme.onSurface)),
      ],
    );
  }
}

class _SwitchRow extends StatelessWidget {
  final String label;
  final Widget? subtitle;
  final bool value;
  final ValueChanged<bool> onChanged;

  const _SwitchRow({
    required this.label,
    required this.value,
    required this.onChanged,
    this.subtitle,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(label, style: Theme.of(context).textTheme.bodyMedium),
                if (subtitle != null) subtitle!,
              ],
            ),
          ),
          Switch(value: value, onChanged: onChanged),
        ],
      ),
    );
  }
}
