import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/join_form_question.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/join_form_provider.dart';

class JoinFormAdminNotifier extends AsyncNotifier<List<JoinFormQuestion>> {
  @override
  Future<List<JoinFormQuestion>> build() async {
    final api = ref.read(apiClientProvider);
    final response = await api.get('/api/community/join-form/');
    final data = response.data as List<dynamic>;
    return data
        .map((item) => JoinFormQuestion.fromJson(item as Map<String, dynamic>))
        .toList();
  }

  Future<void> addQuestion({
    required String label,
    String fieldType = 'text',
    List<String> options = const [],
    bool required = false,
  }) async {
    final api = ref.read(apiClientProvider);
    await api.post(
      '/api/community/join-form/questions/',
      data: {
        'label': label,
        'field_type': fieldType,
        'options': options,
        'required': required,
      },
    );
    ref.invalidate(joinFormProvider);
    ref.invalidateSelf();
  }

  Future<void> updateQuestion({
    required String id,
    required String label,
    String fieldType = 'text',
    List<String> options = const [],
    bool required = false,
  }) async {
    final api = ref.read(apiClientProvider);
    await api.patch(
      '/api/community/join-form/questions/$id/',
      data: {
        'label': label,
        'field_type': fieldType,
        'options': options,
        'required': required,
      },
    );
    ref.invalidate(joinFormProvider);
    ref.invalidateSelf();
  }

  Future<void> deleteQuestion(String id) async {
    final api = ref.read(apiClientProvider);
    await api.delete('/api/community/join-form/questions/$id/');
    ref.invalidate(joinFormProvider);
    ref.invalidateSelf();
  }

  Future<void> reorder(List<String> questionIds) async {
    final api = ref.read(apiClientProvider);
    await api.put(
      '/api/community/join-form/questions/order/',
      data: {'question_ids': questionIds},
    );
    ref.invalidate(joinFormProvider);
    ref.invalidateSelf();
  }
}

final joinFormAdminProvider =
    AsyncNotifierProvider<JoinFormAdminNotifier, List<JoinFormQuestion>>(
      JoinFormAdminNotifier.new,
    );
