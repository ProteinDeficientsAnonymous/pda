import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:mocktail/mocktail.dart';
import 'package:pda/main.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/providers/home_provider.dart';
import 'package:pda/services/api_client.dart';
import 'package:pda/services/secure_storage.dart';

import 'helpers/fake_secure_storage.dart';

class MockApiClient extends Mock implements ApiClient {}

void main() {
  testWidgets('App renders without crashing', (WidgetTester tester) async {
    final mockApi = MockApiClient();

    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          secureStorageProvider.overrideWithValue(
            SecureStorageService.withStorage(FakeSecureStorage()),
          ),
          apiClientProvider.overrideWithValue(mockApi),
          homePageNotifierProvider.overrideWith(() => _FakeHomeNotifier()),
        ],
        child: const PdaApp(),
      ),
    );
    await tester.pump();
    expect(find.byType(MaterialApp), findsOneWidget);
  });
}

class _FakeHomeNotifier extends HomePageNotifier {
  @override
  Future<HomePage> build() async {
    return HomePage(
      content: 'Test content',
      joinContent: '',
      updatedAt: DateTime(2026),
    );
  }
}
