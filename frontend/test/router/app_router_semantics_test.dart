import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:pda/router/app_router.dart';

void main() {
  test('all GoRoutes have a name for semantic route labelling', () {
    final container = ProviderContainer();
    addTearDown(container.dispose);

    final router = container.read(routerProvider);
    final routes = router.configuration.routes;

    for (final route in routes) {
      if (route is GoRoute) {
        expect(
          route.name,
          isNotNull,
          reason:
              'GoRoute for ${route.path} is missing a name — '
              'this causes a "self-labelled route missing label" '
              'semantics warning',
        );
        expect(
          route.name,
          isNotEmpty,
          reason: 'GoRoute for ${route.path} has an empty name',
        );
      }
    }
  });
}
