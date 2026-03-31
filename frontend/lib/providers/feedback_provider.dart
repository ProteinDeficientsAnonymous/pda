import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/services/api_error.dart';

class FeedbackSubmission {
  final String title;
  final String description;
  final List<String> feedbackTypes;
  final String currentRoute;
  final String userAgent;
  final String userDisplayName;
  final String userPhone;
  final String appVersion;

  const FeedbackSubmission({
    required this.title,
    this.description = '',
    this.feedbackTypes = const [],
    this.currentRoute = '',
    this.userAgent = '',
    this.userDisplayName = '',
    this.userPhone = '',
    this.appVersion = '',
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
          'feedback_types': submission.feedbackTypes,
          'metadata': {
            'route': submission.currentRoute,
            'user_agent': submission.userAgent,
            'user_display_name': submission.userDisplayName,
            'user_phone': submission.userPhone,
            'app_version': submission.appVersion,
          },
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
