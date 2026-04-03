import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/survey.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/config/constants.dart';

class SurveyAdminNotifier extends AsyncNotifier<List<Survey>> {
  @override
  Future<List<Survey>> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/surveys/admin/');
    final data = response.data as List<dynamic>;
    return data
        .map((item) => Survey.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<Survey> createSurvey({
    required String title,
    required String slug,
    String description = '',
    String visibility = PageVisibility.public_,
    String? linkedEventId,
    bool oneResponsePerUser = false,
  }) async {
    final api = ref.read(apiClientProvider);
    final response = await api.post(
      '/api/community/surveys/',
      data: {
        'title': title,
        'slug': slug,
        'description': description,
        'visibility': visibility,
        'one_response_per_user': oneResponsePerUser,
        if (linkedEventId != null) 'linked_event_id': linkedEventId,
      },
    );
    ref.invalidateSelf();
    return Survey.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> updateSurvey(String id, Map<String, dynamic> updates) async {
    final api = ref.read(apiClientProvider);
    await api.patch('/api/community/surveys/$id/', data: updates);
    ref.invalidateSelf();
  }

  Future<void> deleteSurvey(String id) async {
    final api = ref.read(apiClientProvider);
    await api.delete('/api/community/surveys/$id/');
    ref.invalidateSelf();
  }
}

final surveyAdminProvider =
    AsyncNotifierProvider<SurveyAdminNotifier, List<Survey>>(
      SurveyAdminNotifier.new,
    );

/// Fetches a single survey with its questions (admin detail view).
final surveyDetailAdminProvider = FutureProvider.family<Survey, String>((
  ref,
  surveyId,
) async {
  final api = ref.watch(apiClientProvider);
  final response = await api.get('/api/community/surveys/$surveyId/admin/');
  return Survey.fromJson(response.data as Map<String, dynamic>);
});

class SurveyQuestionsNotifier extends AsyncNotifier<Survey> {
  SurveyQuestionsNotifier(this._surveyId);
  final String _surveyId;

  @override
  Future<Survey> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/surveys/$_surveyId/admin/');
    return Survey.fromJson(response.data as Map<String, dynamic>);
  }

  Future<void> addQuestion({
    required String label,
    String fieldType = FieldType.text,
    List<String> options = const [],
    bool required = false,
  }) async {
    final api = ref.read(apiClientProvider);
    await api.post(
      '/api/community/surveys/$_surveyId/questions/',
      data: {
        'label': label,
        'field_type': fieldType,
        'options': options,
        'required': required,
      },
    );
    ref.invalidateSelf();
  }

  Future<void> updateQuestion({
    required String questionId,
    required String label,
    String fieldType = FieldType.text,
    List<String> options = const [],
    bool required = false,
  }) async {
    final api = ref.read(apiClientProvider);
    await api.patch(
      '/api/community/surveys/$_surveyId/questions/$questionId/',
      data: {
        'label': label,
        'field_type': fieldType,
        'options': options,
        'required': required,
      },
    );
    ref.invalidateSelf();
  }

  Future<void> deleteQuestion(String questionId) async {
    final api = ref.read(apiClientProvider);
    await api.delete(
      '/api/community/surveys/$_surveyId/questions/$questionId/',
    );
    ref.invalidateSelf();
  }

  Future<void> reorder(List<String> questionIds) async {
    final api = ref.read(apiClientProvider);
    await api.put(
      '/api/community/surveys/$_surveyId/questions/order/',
      data: {'question_ids': questionIds},
    );
    ref.invalidateSelf();
  }
}

final surveyQuestionsProvider =
    AsyncNotifierProvider.family<SurveyQuestionsNotifier, Survey, String>(
      (arg) => SurveyQuestionsNotifier(arg),
    );

/// Fetches survey responses (admin).
final surveyResponsesProvider =
    FutureProvider.family<List<SurveyResponse>, String>((ref, surveyId) async {
      final api = ref.watch(apiClientProvider);
      final response = await api.get(
        '/api/community/surveys/$surveyId/responses/',
      );
      final data = response.data as List<dynamic>;
      return data
          .map((item) => SurveyResponse.fromJson(item as Map<String, dynamic>))
          .toList();
    });
