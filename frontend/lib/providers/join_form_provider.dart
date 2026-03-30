import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/join_form_question.dart';
import 'package:pda/providers/auth_provider.dart';

final joinFormProvider = FutureProvider<List<JoinFormQuestion>>((ref) async {
  final api = ref.read(apiClientProvider);
  final response = await api.get('/api/community/join-form/');
  final data = response.data as List<dynamic>;
  return data
      .map((item) => JoinFormQuestion.fromJson(item as Map<String, dynamic>))
      .toList();
});
