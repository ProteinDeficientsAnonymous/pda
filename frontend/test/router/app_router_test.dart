import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/providers/auth_provider.dart';
import 'package:pda/router/app_router.dart';

void main() {
  test(
    'routerProvider preserves GoRouter instance across auth state changes',
    () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final router1 = container.read(routerProvider);

      // Invalidating authProvider cascades to routerProvider via ref.watch,
      // causing a new GoRouter to be created (the bug).
      // With ref.listen, the router should stay the same.
      container.invalidate(authProvider);
      await Future<void>.delayed(Duration.zero);

      // Force re-evaluation after invalidation
      final router2 = container.read(routerProvider);

      expect(
        identical(router1, router2),
        isTrue,
        reason: 'GoRouter must not be recreated on auth state changes',
      );
    },
  );
}
