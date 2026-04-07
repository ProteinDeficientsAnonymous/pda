import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:logging/logging.dart';
import 'package:pda/models/join_form_question.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/join_form_provider.dart';
import 'package:pda/config/constants.dart';

final _log = Logger('JoinFormAdmin');

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
    String fieldType = FieldType.text,
    List<String> options = const [],
    bool required = false,
  }) async {
    final api = ref.read(apiClientProvider);
    try {
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
      _log.info('added join form question "$label"');
    } catch (e, st) {
      _log.warning('failed to add join form question "$label"', e, st);
      rethrow;
    }
  }

  Future<void> updateQuestion({
    required String id,
    required String label,
    String fieldType = FieldType.text,
    List<String> options = const [],
    bool required = false,
  }) async {
    final api = ref.read(apiClientProvider);
    try {
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
      _log.info('updated join form question $id');
    } catch (e, st) {
      _log.warning('failed to update join form question $id', e, st);
      rethrow;
    }
  }

  Future<void> deleteQuestion(String id) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.delete('/api/community/join-form/questions/$id/');
      ref.invalidate(joinFormProvider);
      ref.invalidateSelf();
      _log.info('deleted join form question $id');
    } catch (e, st) {
      _log.warning('failed to delete join form question $id', e, st);
      rethrow;
    }
  }

  Future<void> reorder(List<String> questionIds) async {
    final api = ref.read(apiClientProvider);
    try {
      await api.put(
        '/api/community/join-form/questions/order/',
        data: {'question_ids': questionIds},
      );
      ref.invalidate(joinFormProvider);
      ref.invalidateSelf();
    } catch (e, st) {
      _log.warning('failed to reorder join form questions', e, st);
      rethrow;
    }
  }
}

final joinFormAdminProvider =
    AsyncNotifierProvider<JoinFormAdminNotifier, List<JoinFormQuestion>>(
      JoinFormAdminNotifier.new,
    );
