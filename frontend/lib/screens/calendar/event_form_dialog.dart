import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';
import 'package:intl/intl.dart';
import 'package:pda/models/event.dart';
import 'package:pda/config/constants.dart';
import 'package:pda/providers/event_poll_provider.dart';
import 'package:pda/screens/calendar/event_form_result.dart';
import 'package:pda/screens/calendar/event_form_photo_section.dart';
import 'package:pda/screens/calendar/event_form_when_section.dart';
import 'package:pda/screens/calendar/event_form_location_field.dart';
import 'package:pda/screens/calendar/event_form_links_section.dart';
import 'package:pda/screens/calendar/event_form_settings_section.dart';
import 'package:pda/utils/validators.dart' as v;
import 'package:pda/widgets/photo_crop_dialog.dart';

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
  bool _initialShowCost = false;
  late DateTime _start;
  late DateTime? _end;
  late bool _rsvpEnabled;
  late bool _allowPlusOnes;
  late bool _datetimeTbd;
  late String _visibilityChoice;
  late String _invitePermission;
  late Set<String> _coHostIds;
  late Map<String, String> _coHostNames;
  late Set<String> _invitedUserIds;
  XFile? _selectedPhoto;
  bool _removePhoto = false;
  bool _removingPoll = false;
  late bool _showDetails;
  double? _latitude;
  double? _longitude;
  final List<DateTime> _datetimePollOptions = [];

  bool get _isEdit => widget.event != null;

  @override
  void initState() {
    super.initState();
    _showDetails = widget.event != null;
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
      _initialShowCost =
          e.price.isNotEmpty ||
          e.venmoLink.isNotEmpty ||
          e.cashappLink.isNotEmpty ||
          e.zelleInfo.isNotEmpty;
      _start = e.startDatetime.toLocal();
      _end = e.endDatetime?.toLocal();
      _rsvpEnabled = e.rsvpEnabled;
      _allowPlusOnes = e.allowPlusOnes;
      _datetimeTbd = e.datetimeTbd;
      _visibilityChoice = fieldsToVisibilityChoice(e.visibility, e.eventType);
      _invitePermission = e.invitePermission;
      _coHostIds = Set<String>.from(e.coHostIds);
      _coHostNames = {
        for (var i = 0; i < e.coHostIds.length; i++)
          if (i < e.coHostNames.length) e.coHostIds[i]: e.coHostNames[i],
      };
      _invitedUserIds = Set<String>.from(e.invitedUserIds);
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
      _allowPlusOnes = false;
      _datetimeTbd = false;
      _visibilityChoice = EventVisibilityChoice.public_;
      _invitePermission = InvitePermission.allMembers;
      _coHostIds = {};
      _coHostNames = {};
      _invitedUserIds = {};
    }
  }

  @override
  void dispose() {
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
    final (visibility, eventType) = visibilityChoiceToFields(_visibilityChoice);
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
          'allow_plus_ones': _allowPlusOnes,
          'datetime_tbd': _datetimeTbd || _datetimePollOptions.isNotEmpty,
          'event_type': eventType,
          'visibility': visibility,
          'invite_permission': _invitePermission,
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
    if (image == null) return;
    final rawBytes = await image.readAsBytes();
    if (!mounted) return;
    final croppedBytes = await showPhotoCropDialog(
      context: context,
      imageBytes: rawBytes,
      mode: PhotoCropMode.rectangle,
      maxHeightRatio: 5 / 4,
    );
    if (croppedBytes == null) return;

    final croppedFile = XFile.fromData(
      croppedBytes,
      name: image.name,
      mimeType: image.mimeType,
    );
    setState(() {
      _selectedPhoto = croppedFile;
      _removePhoto = false;
    });
  }

  @override
  Widget build(BuildContext context) {
    String dateFmt(DateTime d) =>
        DateFormat('EEE, MMM d, y').format(d).toLowerCase();
    final screenWidth = MediaQuery.sizeOf(context).width;
    final dialogWidth = screenWidth < 640
        ? screenWidth - 48
        : screenWidth < 1024
        ? screenWidth * 0.7
        : 720.0;

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
                EventFormPhotoSection(
                  existingPhotoUrl: widget.event?.photoUrl ?? '',
                  selectedPhoto: _selectedPhoto,
                  removePhoto: _removePhoto,
                  onPickPhoto: _pickPhoto,
                  onRemovePhoto: () => setState(() {
                    _selectedPhoto = null;
                    _removePhoto = true;
                  }),
                ),
                TextFormField(
                  controller: _title,
                  decoration: const InputDecoration(
                    labelText: 'what\'s the event? *',
                    border: OutlineInputBorder(),
                  ),
                  textCapitalization: TextCapitalization.sentences,
                  validator: v.all([v.required(), v.maxLength(300)]),
                ),
                const SizedBox(height: 16),
                EventFormWhenSection(
                  isEdit: _isEdit,
                  event: widget.event,
                  start: _start,
                  end: _end,
                  datetimeTbd: _datetimeTbd,
                  datetimePollOptions: _datetimePollOptions,
                  removingPoll: _removingPoll,
                  onStartChanged: (dt) => setState(() {
                    _start = dt;
                    if (_end != null && _end!.isBefore(_start)) {
                      _end = _start.add(const Duration(hours: 1));
                    }
                  }),
                  onEndChanged: (dt) => setState(() => _end = dt),
                  onAddEndTime: () => setState(() {
                    _end = _start.add(const Duration(hours: 1));
                  }),
                  onClearEndTime: () => setState(() => _end = null),
                  onPollOptionsChanged: (options) => setState(() {
                    _datetimePollOptions
                      ..clear()
                      ..addAll(options);
                  }),
                  onRemovePoll: () => _removePoll(context),
                  pickerWidth: dialogWidth,
                  dateFmt: dateFmt,
                ),
                const SizedBox(height: 16),
                EventFormLocationField(
                  controller: _location,
                  onLocationSelected: (coords) => setState(() {
                    _latitude = coords.lat;
                    _longitude = coords.lon;
                  }),
                ),
                const SizedBox(height: 16),
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
                const SizedBox(height: 8),
                Center(
                  child: TextButton.icon(
                    onPressed: () =>
                        setState(() => _showDetails = !_showDetails),
                    icon: Icon(
                      _showDetails ? Icons.expand_less : Icons.expand_more,
                      size: 18,
                    ),
                    label: Text(
                      _showDetails ? 'fewer details' : 'more details',
                    ),
                  ),
                ),
                if (_showDetails) ...[
                  const SizedBox(height: 8),
                  EventFormLinksAndCostSection(
                    whatsappLink: _whatsappLink,
                    partifulLink: _partifulLink,
                    otherLink: _otherLink,
                    price: _price,
                    venmoLink: _venmoLink,
                    cashappLink: _cashappLink,
                    zelleInfo: _zelleInfo,
                    rsvpEnabled: _rsvpEnabled,
                    initialShowCost: _initialShowCost,
                    normalizeUrl: _normalizeUrl,
                  ),
                  EventFormSettingsSection(
                    rsvpEnabled: _rsvpEnabled,
                    allowPlusOnes: _allowPlusOnes,
                    visibilityChoice: _visibilityChoice,
                    partifulLinkText: _partifulLink.text,
                    invitePermission: _invitePermission,
                    coHostIds: _coHostIds,
                    coHostNames: _coHostNames,
                    scrollController: _scrollController,
                    onRsvpChanged: (val) => setState(() => _rsvpEnabled = val),
                    onAllowPlusOnesChanged: (val) =>
                        setState(() => _allowPlusOnes = val),
                    onVisibilityChoiceChanged: (val) =>
                        setState(() => _visibilityChoice = val),
                    onInvitePermissionChanged: (val) =>
                        setState(() => _invitePermission = val),
                    onCoHostsChanged: (ids) => setState(() => _coHostIds = ids),
                  ),
                ],
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
