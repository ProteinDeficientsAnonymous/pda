import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/screens/calendar/event_colors.dart';

class EventFormSettingsSection extends ConsumerWidget {
  final bool rsvpEnabled;
  final String visibilityChoice;
  final String partifulLinkText;
  final String invitePermission;
  final bool allowPlusOnes;
  final int? maxAttendees;
  final ValueChanged<bool> onRsvpChanged;
  final ValueChanged<bool> onAllowPlusOnesChanged;
  final ValueChanged<String> onVisibilityChoiceChanged;
  final ValueChanged<String> onInvitePermissionChanged;
  final ValueChanged<int?> onMaxAttendeesChanged;

  const EventFormSettingsSection({
    super.key,
    required this.rsvpEnabled,
    required this.allowPlusOnes,
    required this.visibilityChoice,
    required this.partifulLinkText,
    required this.invitePermission,
    required this.maxAttendees,
    required this.onRsvpChanged,
    required this.onAllowPlusOnesChanged,
    required this.onVisibilityChoiceChanged,
    required this.onInvitePermissionChanged,
    required this.onMaxAttendeesChanged,
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
                  const SizedBox(height: 8),
                  _MaxAttendeesField(
                    value: maxAttendees,
                    onChanged: onMaxAttendeesChanged,
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
              DropdownMenuItem(
                value: EventVisibilityChoice.official,
                child: _ColorDotLabel(
                  label: 'official PDA event',
                  choice: EventVisibilityChoice.official,
                  brightness: theme.brightness,
                ),
              ),
            DropdownMenuItem(
              value: EventVisibilityChoice.public_,
              child: _ColorDotLabel(
                label: 'public',
                choice: EventVisibilityChoice.public_,
                brightness: theme.brightness,
              ),
            ),
            DropdownMenuItem(
              value: EventVisibilityChoice.membersOnly,
              child: _ColorDotLabel(
                label: 'pda members only',
                choice: EventVisibilityChoice.membersOnly,
                brightness: theme.brightness,
              ),
            ),
            DropdownMenuItem(
              value: EventVisibilityChoice.inviteOnly,
              child: _ColorDotLabel(
                label: 'invite only',
                choice: EventVisibilityChoice.inviteOnly,
                brightness: theme.brightness,
              ),
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

class _MaxAttendeesField extends StatefulWidget {
  final int? value;
  final ValueChanged<int?> onChanged;

  const _MaxAttendeesField({required this.value, required this.onChanged});

  @override
  State<_MaxAttendeesField> createState() => _MaxAttendeesFieldState();
}

class _MaxAttendeesFieldState extends State<_MaxAttendeesField> {
  late final TextEditingController _controller;

  @override
  void initState() {
    super.initState();
    _controller = TextEditingController(
      text: widget.value != null ? widget.value.toString() : '',
    );
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return TextFormField(
      controller: _controller,
      decoration: const InputDecoration(
        labelText: 'max attendees',
        helperText: 'leave empty for no limit',
        counterText: '',
      ),
      keyboardType: TextInputType.number,
      inputFormatters: [FilteringTextInputFormatter.digitsOnly],
      maxLength: 5,
      onChanged: (val) {
        final parsed = int.tryParse(val);
        widget.onChanged(parsed);
      },
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

class _ColorDotLabel extends StatelessWidget {
  final String label;
  final String choice;
  final Brightness brightness;

  const _ColorDotLabel({
    required this.label,
    required this.choice,
    required this.brightness,
  });

  @override
  Widget build(BuildContext context) {
    final (type, vis) = visibilityChoiceToFields(choice);
    final (bg, _) = eventColors(type, vis, brightness);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        Container(
          width: 12,
          height: 12,
          decoration: BoxDecoration(color: bg, shape: BoxShape.circle),
        ),
        const SizedBox(width: 8),
        Text(label),
      ],
    );
  }
}
