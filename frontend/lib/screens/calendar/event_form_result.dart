import 'package:image_picker/image_picker.dart';

/// Result returned by [EventFormDialog] — JSON data + optional photo.
class EventFormResult {
  final Map<String, dynamic> data;
  final XFile? photo;
  final bool removePhoto;
  final List<String> datetimePollOptions;

  /// 'active' to publish immediately, 'draft' to save as draft.
  final String status;

  const EventFormResult({
    required this.data,
    this.photo,
    this.removePhoto = false,
    this.datetimePollOptions = const [],
    this.status = 'active',
  });
}
