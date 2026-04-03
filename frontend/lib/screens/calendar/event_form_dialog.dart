import 'dart:async';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/utils/time_format.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/config/constants.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/screens/calendar/event_form_result.dart';
import 'package:pda/screens/calendar/event_form_models.dart';
import 'package:pda/screens/calendar/co_host_picker.dart';
import 'package:pda/screens/calendar/live_poll_editor.dart';
import 'package:pda/screens/calendar/event_form_field_sections.dart';
import 'package:pda/widgets/date_time_picker.dart';
import 'package:pda/widgets/date_time_picker_dialog.dart';

export 'package:pda/screens/calendar/event_form_result.dart'
    show EventFormResult;

/// Shared form dialog for creating and editing events.
/// Pass [event] to pre-fill fields for editing; omit for create mode.
class EventFormDialog extends ConsumerStatefulWidget {
  final Event? event;
  final DateTime? initialDate;

  const EventFormDialog({super.key, this.event, this.initialDate});

  @override
  ConsumerState<EventFormDialog> createState() => _EventFormDialogState();
}

class _EventFormDialogState extends ConsumerState<EventFormDialog> {
  final _formKey = GlobalKey<FormState>();
  final _scrollController = ScrollController();
  late final TextEditingController _title;
  late final TextEditingController _description;
  late final TextEditingController _location;
  late final TextEditingController _whatsappLink;
  late final TextEditingController _partifulLink;
  late final TextEditingController _otherLink;
  late final TextEditingController _price;
  late final TextEditingController _venmoLink;
  late final TextEditingController _cashappLink;
  late final TextEditingController _zelleInfo;
  bool _showCost = false;
  late DateTime _start;
  late DateTime? _end;
  late bool _rsvpEnabled;
  late bool _datetimeTbd;
  late String _eventType;
  late String _visibility;
  late Set<String> _coHostIds;
  late Map<String, String> _coHostNames;
  late Set<String> _invitedUserIds;
  late Map<String, String> _invitedUserNames;
  DateTimePickerMode? _startPickerMode;
  DateTimePickerMode? _endPickerMode;
  XFile? _selectedPhoto;
  bool _removePhoto = false;
  bool _removingPoll = false;
  double? _latitude;
  double? _longitude;
  List<EventPhotonResult> _locationResults = [];
  bool _locationSearching = false;
  Timer? _debounceTimer;
  final List<DateTime> _datetimePollOptions = [];

  bool get _isEdit => widget.event != null;

  @override
  void initState() {
    super.initState();
    final e = widget.event;
    if (e != null) {
      _title = TextEditingController(text: e.title);
      _description = TextEditingController(text: e.description);
      _location = TextEditingController(text: e.location);
      _whatsappLink = TextEditingController(text: e.whatsappLink);
      _partifulLink = TextEditingController(text: e.partifulLink)
        ..addListener(() => setState(() {}));
      _otherLink = TextEditingController(text: e.otherLink);
      _price = TextEditingController(text: e.price);
      _venmoLink = TextEditingController(
        text: _extractHandle(e.venmoLink, 'venmo.com/'),
      );
      _cashappLink = TextEditingController(
        text: _extractHandle(e.cashappLink, r'cash.app/$'),
      );
      _zelleInfo = TextEditingController(text: e.zelleInfo);
      _showCost =
          e.price.isNotEmpty ||
          e.venmoLink.isNotEmpty ||
          e.cashappLink.isNotEmpty ||
          e.zelleInfo.isNotEmpty;
      _start = e.startDatetime.toLocal();
      _end = e.endDatetime?.toLocal();
      _rsvpEnabled = e.rsvpEnabled;
      _datetimeTbd = e.datetimeTbd;
      _eventType = e.eventType;
      _visibility = e.visibility;
      _coHostIds = Set<String>.from(e.coHostIds);
      _coHostNames = {
        for (var i = 0; i < e.coHostIds.length; i++)
          if (i < e.coHostNames.length) e.coHostIds[i]: e.coHostNames[i],
      };
      _invitedUserIds = Set<String>.from(e.invitedUserIds);
      _invitedUserNames = {
        for (var i = 0; i < e.invitedUserIds.length; i++)
          if (i < e.invitedUserNames.length)
            e.invitedUserIds[i]: e.invitedUserNames[i],
      };
      _latitude = e.latitude;
      _longitude = e.longitude;
    } else {
      _title = TextEditingController();
      _description = TextEditingController();
      _location = TextEditingController();
      _whatsappLink = TextEditingController();
      _partifulLink = TextEditingController()
        ..addListener(() => setState(() {}));
      _otherLink = TextEditingController();
      _price = TextEditingController();
      _venmoLink = TextEditingController();
      _cashappLink = TextEditingController();
      _zelleInfo = TextEditingController();
      final base = widget.initialDate ?? DateTime.now();
      final now = DateTime.now();
      _start = DateTime(base.year, base.month, base.day, now.hour + 1);
      _end = null;
      _rsvpEnabled = false;
      _datetimeTbd = false;
      _eventType = EventType.community;
      _visibility = PageVisibility.public_;
      _coHostIds = {};
      _coHostNames = {};
      _invitedUserIds = {};
      _invitedUserNames = {};
    }
  }

  @override
  void dispose() {
    _debounceTimer?.cancel();
    _scrollController.dispose();
    _title.dispose();
    _description.dispose();
    _location.dispose();
    _whatsappLink.dispose();
    _partifulLink.dispose();
    _otherLink.dispose();
    _price.dispose();
    _venmoLink.dispose();
    _cashappLink.dispose();
    _zelleInfo.dispose();
    super.dispose();
  }

  void _onStartChanged(DateTime dt) {
    setState(() {
      _start = dt;
      if (_end != null && _end!.isBefore(_start)) {
        _end = _start.add(const Duration(hours: 1));
      }
    });
  }

  void _onEndChanged(DateTime dt) {
    setState(() => _end = dt);
  }

  String _normalizeUrl(String raw) {
    final s = raw.trim();
    if (s.isEmpty) return s;
    if (s.startsWith('http://') || s.startsWith('https://')) return s;
    return 'https://$s';
  }

  String _extractHandle(String url, String domain) {
    if (url.isEmpty) return '';
    final idx = url.indexOf(domain);
    if (idx == -1) return url;
    return url.substring(idx + domain.length).replaceAll('/', '');
  }

  String _handleToLink(String handle, String baseUrl) {
    final h = handle.trim().replaceFirst(RegExp(r'^@'), '');
    if (h.isEmpty) return '';
    return '$baseUrl$h';
  }

  void _submit() {
    if (!_formKey.currentState!.validate()) return;
    Navigator.of(context).pop(
      EventFormResult(
        data: {
          'title': _title.text.trim(),
          'description': _description.text.trim(),
          'location': _location.text.trim(),
          'latitude': _latitude,
          'longitude': _longitude,
          'whatsapp_link': _normalizeUrl(_whatsappLink.text),
          'partiful_link': _normalizeUrl(_partifulLink.text),
          'other_link': _normalizeUrl(_otherLink.text),
          'price': _price.text.trim(),
          'venmo_link': _handleToLink(_venmoLink.text, 'https://venmo.com/'),
          'cashapp_link': _handleToLink(
            _cashappLink.text,
            'https://cash.app/\$',
          ),
          'zelle_info': _zelleInfo.text.trim(),
          'start_datetime': _start.toUtc().toIso8601String(),
          'end_datetime': _end?.toUtc().toIso8601String(),
          'rsvp_enabled': _rsvpEnabled,
          'datetime_tbd': _datetimeTbd || _datetimePollOptions.isNotEmpty,
          'event_type': _eventType,
          'visibility': _visibility,
          'co_host_ids': _coHostIds.toList(),
          'invited_user_ids': _invitedUserIds.toList(),
        },
        photo: _selectedPhoto,
        removePhoto: _removePhoto,
        datetimePollOptions: _datetimePollOptions
            .map((dt) => dt.toUtc().toIso8601String())
            .toList(),
      ),
    );
  }

  Future<void> _addDatetimePollOption() async {
    final now = DateTime.now();
    final dt = await showDateTimePicker(
      context: context,
      initialDateTime: now,
      firstDate: DateTime(now.year - 1),
      lastDate: DateTime(now.year + 2),
    );
    if (dt == null || !mounted) return;
    setState(() {
      _datetimePollOptions.add(dt);
    });
  }

  Future<void> _removePoll(BuildContext ctx) async {
    final eventId = widget.event?.id;
    if (eventId == null) return;
    final nav = Navigator.of(ctx);
    final messenger = ScaffoldMessenger.of(ctx);
    final confirmed = await showDialog<bool>(
      context: ctx,
      builder: (dlgCtx) => AlertDialog(
        title: const Text('remove poll?'),
        content: const Text(
          'This will delete the poll and all votes. This cannot be undone.',
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(dlgCtx).pop(false),
            child: const Text('cancel'),
          ),
          TextButton(
            onPressed: () => Navigator.of(dlgCtx).pop(true),
            child: Text(
              'remove',
              style: TextStyle(color: Theme.of(dlgCtx).colorScheme.error),
            ),
          ),
        ],
      ),
    );
    if (confirmed != true || !mounted) return;
    setState(() => _removingPoll = true);
    try {
      await deleteEventPoll(ref: ref, eventId: eventId);
      if (!mounted) return;
      nav.pop();
    } catch (e) {
      if (!mounted) return;
      messenger.showSnackBar(
        const SnackBar(
          content: Text('couldn\'t remove poll — try again'),
          backgroundColor: Colors.red,
        ),
      );
      setState(() => _removingPoll = false);
    }
  }

  Future<void> _pickPhoto() async {
    final image = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      maxWidth: 1200,
      maxHeight: 800,
      imageQuality: 85,
    );
    if (image != null) {
      setState(() {
        _selectedPhoto = image;
        _removePhoto = false;
      });
    }
  }

  void _searchLocation(String query) {
    _debounceTimer?.cancel();
    if (query.trim().length < 3) {
      setState(() {
        _locationResults = [];
        _latitude = null;
        _longitude = null;
      });
      return;
    }
    _debounceTimer = Timer(const Duration(milliseconds: 400), () async {
      if (!mounted) return;
      setState(() => _locationSearching = true);
      try {
        final resp = await Dio().get<Map<String, dynamic>>(
          'https://photon.komoot.io/api/',
          queryParameters: {
            'q': query.trim(),
            'limit': 5,
            'lat': 40.7128, // bias results toward NYC
            'lon': -74.006,
          },
        );
        final features = (resp.data?['features'] as List<dynamic>?) ?? const [];
        if (!mounted) return;
        setState(() {
          _locationResults = features.map((f) {
            final props = f['properties'] as Map<String, dynamic>;
            final coords = f['geometry']['coordinates'] as List<dynamic>;
            final name = props['name'] as String? ?? '';
            final city = props['city'] as String?;
            final parts = <String>[
              if (name.isNotEmpty) name,
              if (city != null) city,
              if (props['state'] != null) props['state'] as String,
              if (props['country'] != null) props['country'] as String,
            ];
            return EventPhotonResult(
              name: name,
              city: city != null && city != name ? city : null,
              fullAddress: parts.join(', '),
              lat: (coords[1] as num).toDouble(),
              lon: (coords[0] as num).toDouble(),
            );
          }).toList();
        });
      } catch (_) {
        if (mounted) setState(() => _locationResults = []);
      } finally {
        if (mounted) setState(() => _locationSearching = false);
      }
    });
  }

  List<Widget> _buildWhenSection(
    ThemeData theme,
    String Function(DateTime) dateFmt,
    double pickerWidth,
  ) {
    // Editing an event with a poll.
    if (_isEdit && (widget.event?.hasPoll ?? false)) {
      // Poll finalized — datetime_tbd is false, show normal date + note.
      if (!(widget.event?.datetimeTbd ?? true)) {
        return [
          ..._buildDateTimeSection(dateFmt, pickerWidth),
          const SizedBox(height: 4),
          Row(
            children: [
              Icon(
                Icons.check_circle_outline,
                size: 14,
                color: theme.colorScheme.primary,
              ),
              const SizedBox(width: 5),
              Text(
                'set by poll',
                style: theme.textTheme.bodySmall?.copyWith(
                  color: theme.colorScheme.primary,
                ),
              ),
            ],
          ),
        ];
      }
      // Poll still active — show live editor.
      return [
        LivePollEditor(
          eventId: widget.event!.id,
          onRemovePoll: () => _removePoll(context),
          removingPoll: _removingPoll,
        ),
      ];
    }

    // Building a poll — hide date pickers, show poll options.
    if (_datetimePollOptions.isNotEmpty) {
      return [
        Row(
          children: [
            Expanded(
              child: Text('time options', style: theme.textTheme.titleSmall),
            ),
            TextButton(
              onPressed: () => setState(() => _datetimePollOptions.clear()),
              child: const Text('cancel poll'),
            ),
          ],
        ),
        Text(
          'members will vote on these — date is set when you pick a winner',
          style: theme.textTheme.bodySmall?.copyWith(
            color: theme.colorScheme.onSurfaceVariant,
          ),
        ),
        const SizedBox(height: 8),
        for (var i = 0; i < _datetimePollOptions.length; i++)
          Row(
            children: [
              const Icon(Icons.access_time_outlined, size: 16),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  pollDateFmt.format(_datetimePollOptions[i]).toLowerCase(),
                ),
              ),
              IconButton(
                tooltip: 'remove option',
                icon: const Icon(Icons.close, size: 18),
                onPressed: () =>
                    setState(() => _datetimePollOptions.removeAt(i)),
              ),
            ],
          ),
        TextButton.icon(
          onPressed: _addDatetimePollOption,
          icon: const Icon(Icons.add),
          label: const Text('add another time'),
        ),
      ];
    }

    // Default: date/time pickers + offer to switch to a poll.
    return [
      ..._buildDateTimeSection(dateFmt, pickerWidth),
      const SizedBox(height: 10),
      InkWell(
        onTap: _addDatetimePollOption,
        borderRadius: BorderRadius.circular(24),
        child: Semantics(
          button: true,
          label: 'poll members for a time',
          child: Container(
            padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 8),
            decoration: BoxDecoration(
              borderRadius: BorderRadius.circular(24),
              border: Border.all(color: theme.colorScheme.outlineVariant),
            ),
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Icon(
                  Icons.poll_outlined,
                  size: 16,
                  color: theme.colorScheme.onSurfaceVariant,
                ),
                const SizedBox(width: 6),
                Text(
                  'or poll members for a time',
                  style: theme.textTheme.bodySmall?.copyWith(
                    color: theme.colorScheme.onSurfaceVariant,
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ];
  }

  void _toggleStartMode(DateTimePickerMode mode) {
    setState(() {
      _startPickerMode = _startPickerMode == mode ? null : mode;
    });
  }

  void _toggleEndMode(DateTimePickerMode mode) {
    setState(() {
      _endPickerMode = _endPickerMode == mode ? null : mode;
    });
  }

  List<Widget> _buildDateTimeSection(
    String Function(DateTime) dateFmt,
    double pickerWidth,
  ) {
    return [
      EventFormDateTimeRow(
        label: 'start',
        date: dateFmt(_start),
        time: formatTime(_start),
        isDateExpanded: _startPickerMode == DateTimePickerMode.dateOnly,
        isTimeExpanded: _startPickerMode == DateTimePickerMode.timeOnly,
        onDateTap: () => _toggleStartMode(DateTimePickerMode.dateOnly),
        onTimeTap: () => _toggleStartMode(DateTimePickerMode.timeOnly),
      ),
      if (_startPickerMode != null) ...[
        const SizedBox(height: 8),
        SizedBox(
          width: pickerWidth,
          child: DateTimePicker(
            initialDateTime: _start,
            onDateTimeChanged: _onStartChanged,
            firstDate: DateTime(2000),
            lastDate: DateTime(2100),
            mode: _startPickerMode!,
          ),
        ),
      ],
      const SizedBox(height: 8),
      ..._buildEndTimeSection(dateFmt, pickerWidth),
    ];
  }

  List<Widget> _buildEndTimeSection(
    String Function(DateTime) dateFmt,
    double pickerWidth,
  ) {
    if (_end == null) {
      return [
        Semantics(
          button: true,
          label: 'add end time',
          child: InkWell(
            onTap: _addEndTime,
            borderRadius: BorderRadius.circular(8),
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 4),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  Icon(
                    Icons.add,
                    size: 16,
                    color: Theme.of(context).colorScheme.primary,
                  ),
                  const SizedBox(width: 6),
                  Text(
                    'add end time',
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).colorScheme.primary,
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ];
    }
    return [
      Row(
        children: [
          Expanded(
            child: EventFormDateTimeRow(
              label: 'end',
              date: dateFmt(_end!),
              time: formatTime(_end!),
              isDateExpanded: _endPickerMode == DateTimePickerMode.dateOnly,
              isTimeExpanded: _endPickerMode == DateTimePickerMode.timeOnly,
              onDateTap: () => _toggleEndMode(DateTimePickerMode.dateOnly),
              onTimeTap: () => _toggleEndMode(DateTimePickerMode.timeOnly),
            ),
          ),
          IconButton(
            icon: const Icon(Icons.close, size: 16),
            tooltip: 'Remove end time',
            onPressed: _clearEndTime,
          ),
        ],
      ),
      if (_endPickerMode != null) ...[
        const SizedBox(height: 8),
        SizedBox(
          width: pickerWidth,
          child: DateTimePicker(
            initialDateTime: _end!,
            onDateTimeChanged: _onEndChanged,
            firstDate: DateTime(2000),
            lastDate: DateTime(2100),
            mode: _endPickerMode!,
          ),
        ),
      ],
    ];
  }

  void _addEndTime() {
    setState(() {
      _end = _start.add(const Duration(hours: 1));
      _endPickerMode = DateTimePickerMode.timeOnly;
    });
  }

  void _clearEndTime() {
    setState(() {
      _end = null;
      _endPickerMode = null;
    });
  }

  Widget _buildPhotoSection() {
    final cs = Theme.of(context).colorScheme;
    final existingUrl = widget.event?.photoUrl ?? '';
    final hasExisting = existingUrl.isNotEmpty && !_removePhoto;
    final hasSelected = _selectedPhoto != null;
    final hasPhoto = hasSelected || hasExisting;

    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Stack(
          children: [
            ClipRRect(
              borderRadius: BorderRadius.circular(12),
              child: hasSelected
                  ? FutureBuilder<List<int>>(
                      future: _selectedPhoto!.readAsBytes(),
                      builder: (ctx, snap) {
                        if (!snap.hasData) {
                          return const SizedBox(
                            height: 160,
                            child: Center(child: CircularProgressIndicator()),
                          );
                        }
                        return Image.memory(
                          snap.data! as dynamic,
                          height: 160,
                          width: double.infinity,
                          fit: BoxFit.cover,
                        );
                      },
                    )
                  : hasExisting
                  ? Image.network(
                      existingUrl,
                      height: 160,
                      width: double.infinity,
                      fit: BoxFit.cover,
                    )
                  : InkWell(
                      onTap: _pickPhoto,
                      borderRadius: BorderRadius.circular(12),
                      child: Container(
                        height: 130,
                        width: double.infinity,
                        decoration: BoxDecoration(
                          color: cs.surfaceContainerHighest.withValues(
                            alpha: 0.3,
                          ),
                          borderRadius: BorderRadius.circular(12),
                          border: Border.all(
                            color: cs.outline.withValues(alpha: 0.2),
                          ),
                        ),
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.add_photo_alternate_outlined,
                              size: 32,
                              color: cs.onSurfaceVariant.withValues(alpha: 0.5),
                            ),
                            const SizedBox(height: 8),
                            Text(
                              'add a cover photo',
                              style: TextStyle(
                                fontSize: 13,
                                color: cs.onSurfaceVariant.withValues(
                                  alpha: 0.5,
                                ),
                              ),
                            ),
                          ],
                        ),
                      ),
                    ),
            ),
            if (hasPhoto)
              Positioned(
                top: 8,
                right: 8,
                child: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    EventFormPhotoButton(
                      tooltip: 'change photo',
                      icon: Icons.photo_outlined,
                      onPressed: _pickPhoto,
                    ),
                    const SizedBox(width: 4),
                    EventFormPhotoButton(
                      tooltip: 'remove photo',
                      icon: Icons.close,
                      onPressed: () {
                        setState(() {
                          _selectedPhoto = null;
                          _removePhoto = true;
                        });
                      },
                    ),
                  ],
                ),
              ),
          ],
        ),
        const SizedBox(height: 16),
      ],
    );
  }

  Widget _buildLocationField() {
    final theme = Theme.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextFormField(
          controller: _location,
          decoration: InputDecoration(
            labelText: 'where?',
            border: const OutlineInputBorder(),
            prefixIcon: const Icon(Icons.place_outlined),
            suffixIcon: _locationSearching
                ? const Padding(
                    padding: EdgeInsets.all(10),
                    child: SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    ),
                  )
                : null,
          ),
          onChanged: _searchLocation,
          validator: v.maxLength(300),
        ),
        if (_locationResults.isNotEmpty) ...[
          const SizedBox(height: 4),
          Container(
            decoration: BoxDecoration(
              border: Border.all(color: theme.colorScheme.outlineVariant),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: _locationResults.map((r) {
                return ListTile(
                  dense: true,
                  title: Text(r.name, style: const TextStyle(fontSize: 13)),
                  subtitle: r.city != null
                      ? Text(
                          r.city!,
                          style: TextStyle(
                            fontSize: 12,
                            color: theme.colorScheme.onSurfaceVariant,
                          ),
                        )
                      : null,
                  onTap: () {
                    _location.text = r.fullAddress;
                    setState(() {
                      _latitude = r.lat;
                      _longitude = r.lon;
                      _locationResults = [];
                    });
                  },
                );
              }).toList(),
            ),
          ),
        ],
      ],
    );
  }

  Widget _buildNoFeesNote(ThemeData theme) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
      decoration: BoxDecoration(
        color: theme.colorScheme.secondaryContainer.withValues(alpha: 0.5),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Icon(
            Icons.info_outline,
            size: 16,
            color: theme.colorScheme.onSecondaryContainer,
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'keep it accessible \u{2728} events should be free or at-cost only '
              '(e.g. splitting the grocery bill). no fees or markups please!',
              style: theme.textTheme.bodySmall?.copyWith(
                color: theme.colorScheme.onSecondaryContainer,
              ),
            ),
          ),
        ],
      ),
    );
  }

  List<Widget> _buildLinksSection(ThemeData theme) {
    return [
      const Divider(),
      const SizedBox(height: 8),
      Text('links', style: theme.textTheme.labelLarge),
      const SizedBox(height: 12),
      TextFormField(
        controller: _whatsappLink,
        decoration: const InputDecoration(
          labelText: 'whatsapp group link (optional)',
          border: OutlineInputBorder(),
          prefixIcon: Icon(Icons.chat_outlined),
        ),
        keyboardType: TextInputType.url,
        validator: (val) {
          if (val == null || val.trim().isEmpty) return null;
          final normalized = _normalizeUrl(val.trim());
          final uri = Uri.tryParse(normalized);
          if (uri == null || !uri.hasAuthority) {
            return 'Enter a valid URL';
          }
          final host = uri.host;
          final isWhatsApp =
              host.contains('whatsapp.com') ||
              host == 'wa.me' ||
              host == 'whats.app';
          if (!isWhatsApp) return 'Must be a WhatsApp link';
          return null;
        },
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _partifulLink,
        decoration: InputDecoration(
          labelText: 'partiful link (optional)',
          border: const OutlineInputBorder(),
          prefixIcon: const Icon(Icons.celebration_outlined),
          helperText: _rsvpEnabled && _partifulLink.text.trim().isNotEmpty
              ? 'consider using app RSVPs instead of partiful'
              : null,
          helperStyle: TextStyle(color: theme.colorScheme.tertiary),
        ),
        keyboardType: TextInputType.url,
        validator: (val) {
          if (val == null || val.trim().isEmpty) return null;
          final normalized = _normalizeUrl(val.trim());
          final uri = Uri.tryParse(normalized);
          if (uri == null || !uri.hasAuthority) {
            return 'Enter a valid URL';
          }
          if (!uri.host.contains('partiful.com')) {
            return 'Must be a Partiful link (partiful.com/...)';
          }
          return null;
        },
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _otherLink,
        decoration: const InputDecoration(
          labelText: 'other link (optional)',
          border: OutlineInputBorder(),
          prefixIcon: Icon(Icons.link),
        ),
        keyboardType: TextInputType.url,
        validator: v.optionalUrl(httpsOnly: true),
      ),
    ];
  }

  List<Widget> _buildCostSection(ThemeData theme) {
    if (!_showCost) {
      return [
        Center(
          child: TextButton.icon(
            onPressed: () => setState(() => _showCost = true),
            icon: const Icon(Icons.attach_money, size: 18),
            label: const Text('add cost'),
          ),
        ),
      ];
    }
    return [
      Row(
        children: [
          Text(
            'cost & payment',
            style: theme.textTheme.labelLarge?.copyWith(
              color: theme.colorScheme.primary,
            ),
          ),
          const Spacer(),
          TextButton(
            onPressed: () {
              setState(() {
                _showCost = false;
                _price.clear();
                _venmoLink.clear();
                _cashappLink.clear();
                _zelleInfo.clear();
              });
            },
            child: const Text('remove'),
          ),
        ],
      ),
      const SizedBox(height: 4),
      Text(
        'costs should only cover shared orders or direct expenses — no fees or markups',
        style: TextStyle(
          fontSize: 12,
          color: theme.colorScheme.onSurface.withValues(alpha: 0.5),
        ),
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _price,
        decoration: const InputDecoration(
          labelText: 'cost',
          hintText: 'e.g. \$5 for groceries',
          border: OutlineInputBorder(),
          prefixIcon: Icon(Icons.attach_money),
        ),
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _venmoLink,
        decoration: const InputDecoration(
          labelText: 'venmo handle',
          hintText: 'username',
          border: OutlineInputBorder(),
          prefixText: '@',
        ),
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _cashappLink,
        decoration: const InputDecoration(
          labelText: 'cash app handle',
          hintText: 'username',
          border: OutlineInputBorder(),
          prefixText: r'$',
        ),
      ),
      const SizedBox(height: 12),
      TextFormField(
        controller: _zelleInfo,
        decoration: const InputDecoration(
          labelText: 'zelle (email or phone)',
          border: OutlineInputBorder(),
          prefixIcon: Icon(Icons.account_balance_outlined),
        ),
      ),
    ];
  }

  Widget _buildRsvpToggle(ThemeData theme) {
    return SwitchListTile(
      value: _rsvpEnabled,
      onChanged: (val) => setState(() => _rsvpEnabled = val),
      title: const Text('enable RSVPs'),
      subtitle: _rsvpEnabled && _partifulLink.text.trim().isNotEmpty
          ? Text(
              'you have a partiful link set — consider using one or the other',
              style: TextStyle(color: theme.colorScheme.tertiary),
            )
          : null,
      contentPadding: EdgeInsets.zero,
    );
  }

  List<Widget> _buildCoHostPicker(ThemeData theme) {
    return [
      const Divider(),
      const SizedBox(height: 8),
      Text('co-hosts', style: theme.textTheme.labelLarge),
      const SizedBox(height: 8),
      CoHostPicker(
        selectedIds: _coHostIds,
        selectedNames: _coHostNames,
        onChanged: (ids) => setState(() => _coHostIds = ids),
        scrollController: _scrollController,
      ),
    ];
  }

  List<Widget> _buildInvitePicker(ThemeData theme) {
    return [
      const Divider(),
      const SizedBox(height: 8),
      Text('invite members', style: theme.textTheme.labelLarge),
      const SizedBox(height: 4),
      Text(
        _visibility == PageVisibility.inviteOnly
            ? 'only invited members (plus you and co-hosts) will see this event'
            : 'invited list is only visible to you and co-hosts',
        style: TextStyle(
          fontSize: 12,
          color: theme.colorScheme.onSurfaceVariant,
        ),
      ),
      const SizedBox(height: 8),
      CoHostPicker(
        selectedIds: _invitedUserIds,
        selectedNames: _invitedUserNames,
        onChanged: (ids) => setState(() => _invitedUserIds = ids),
        scrollController: _scrollController,
      ),
    ];
  }

  @override
  Widget build(BuildContext context) {
    String dateFmt(DateTime d) =>
        DateFormat('EEE, MMM d, y').format(d).toLowerCase();
    final theme = Theme.of(context);

    final screenWidth = MediaQuery.sizeOf(context).width;
    final dialogWidth = screenWidth < 520 ? screenWidth - 48 : 480.0;

    return AlertDialog(
      title: Text(_isEdit ? 'edit event' : 'new event \u{1F331}'),
      contentPadding: const EdgeInsets.fromLTRB(24, 16, 24, 16),
      clipBehavior: Clip.none,
      content: ConstrainedBox(
        constraints: BoxConstraints(
          maxWidth: dialogWidth,
          maxHeight: MediaQuery.sizeOf(context).height * 0.7,
        ),
        child: Form(
          key: _formKey,
          child: SingleChildScrollView(
            controller: _scrollController,
            child: Column(
              mainAxisSize: MainAxisSize.min,
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                _buildPhotoSection(),
                TextFormField(
                  controller: _title,
                  decoration: const InputDecoration(
                    labelText: 'what\'s the event? *',
                    border: OutlineInputBorder(),
                  ),
                  textCapitalization: TextCapitalization.sentences,
                  validator: v.all([v.required(), v.maxLength(300)]),
                ),
                const SizedBox(height: 12),
                _buildNoFeesNote(theme),
                const SizedBox(height: 16),
                ..._buildWhenSection(theme, dateFmt, dialogWidth),
                const SizedBox(height: 16),
                _buildLocationField(),
                const SizedBox(height: 12),
                TextFormField(
                  controller: _description,
                  decoration: const InputDecoration(
                    labelText: 'tell us more',
                    border: OutlineInputBorder(),
                    alignLabelWithHint: true,
                  ),
                  maxLines: 3,
                  textCapitalization: TextCapitalization.sentences,
                  validator: v.maxLength(2000),
                ),
                const SizedBox(height: 16),
                ..._buildLinksSection(theme),
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                ..._buildCostSection(theme),
                const SizedBox(height: 16),
                const Divider(),
                const SizedBox(height: 8),
                _buildRsvpToggle(theme),
                const SizedBox(height: 8),
                DropdownButtonFormField<String>(
                  initialValue: _visibility,
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
                  onChanged: (val) => setState(
                    () => _visibility = val ?? PageVisibility.public_,
                  ),
                ),
                if (ref
                        .watch(authProvider)
                        .value
                        ?.hasPermission(Permission.tagOfficialEvent) ??
                    false) ...[
                  const SizedBox(height: 8),
                  SwitchListTile(
                    title: const Text('official PDA event'),
                    subtitle: const Text(
                      'mark as an official PDA-organized event',
                    ),
                    value: _eventType == EventType.official,
                    contentPadding: EdgeInsets.zero,
                    onChanged: (val) => setState(
                      () => _eventType = val
                          ? EventType.official
                          : EventType.community,
                    ),
                  ),
                ],
                const SizedBox(height: 16),
                ..._buildCoHostPicker(theme),
                const SizedBox(height: 8),
                ..._buildInvitePicker(theme),
                const SizedBox(height: 8),
              ],
            ),
          ),
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: const Text('Cancel'),
        ),
        FilledButton(onPressed: _submit, child: Text(_isEdit ? 'save' : 'add')),
      ],
    );
  }
}
