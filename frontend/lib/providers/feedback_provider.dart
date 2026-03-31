import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';

class FeedbackAttachment {
  final String filename;
  final String contentType;
  final String base64Data;

  const FeedbackAttachment({
    required this.filename,
    required this.contentType,
    required this.base64Data,
  });

  Map<String, dynamic> toJson() => {
    'filename': filename,
    'content_type': contentType,
    'data': base64Data,
  };
}

class FeedbackSubmission {
  final String title;
  final String description;
  final String currentRoute;
  final String userAgent;
  final String userDisplayName;
  final String userPhone;
  final String appVersion;
  final List<FeedbackAttachment> attachments;

  const FeedbackSubmission({
    required this.title,
    this.description = '',
    this.currentRoute = '',
    this.userAgent = '',
    this.userDisplayName = '',
    this.userPhone = '',
    this.appVersion = '',
    this.attachments = const [],
  });
}

class FeedbackNotifier extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> submit(FeedbackSubmission submission) async {
    state = const AsyncLoading();
    final api = ref.read(apiClientProvider);
    try {
      await api.post(
        '/api/community/feedback/',
        data: {
          'title': submission.title,
          'description': submission.description,
          'metadata': {
            'route': submission.currentRoute,
            'user_agent': submission.userAgent,
            'user_display_name': submission.userDisplayName,
            'user_phone': submission.userPhone,
            'app_version': submission.appVersion,
          },
          'attachments': submission.attachments.map((a) => a.toJson()).toList(),
        },
      );
      state = const AsyncData(null);
    } catch (e, st) {
      state = AsyncError(ApiError.from(e), st);
    }
  }
}

final feedbackProvider = AsyncNotifierProvider<FeedbackNotifier, void>(
  FeedbackNotifier.new,
);
