import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:pda/models/join_request.dart';
import 'package:pda/providers/auth_provider.dart';

final joinRequestsProvider = FutureProvider<List<JoinRequest>>((ref) async {
  final api = ref.watch(apiClientProvider);
  final response = await api.get('/api/community/join-requests/');
  final data = response.data as List<dynamic>;
  return data
      .map((item) => JoinRequest.fromJson(item as Map<String, dynamic>))
      .toList();
});
