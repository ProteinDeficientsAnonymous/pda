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

class FeedbackNotifier extends AsyncNotifier<void> {
  @override
  Future<void> build() async {}

  Future<void> submit({
    required String title,
    String description = '',
    String currentRoute = '',
    String userAgent = '',
    String userDisplayName = '',
    String userPhone = '',
    String appVersion = '',
    List<FeedbackAttachment> attachments = const [],
  }) async {
    state = const AsyncLoading();
    final api = ref.read(apiClientProvider);
    try {
      final metadata = <String, dynamic>{
        'route': currentRoute,
        'user_agent': userAgent,
        'user_display_name': userDisplayName,
        'user_phone': userPhone,
        'app_version': appVersion,
      };

      await api.post(
        '/api/community/feedback/',
        data: {
          'title': title,
          'description': description,
          'metadata': metadata,
          'attachments': attachments.map((a) => a.toJson()).toList(),
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
