import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:pda/providers/accessibility_preferences_provider.dart';
import 'package:shared_preferences/shared_preferences.dart';

void main() {
  group('AccessibilityPreferencesNotifier', () {
    setUp(() {
      SharedPreferences.setMockInitialValues({});
    });

    test('defaults to ThemeMode.system', () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      final prefs = await container.read(
        accessibilityPreferencesProvider.future,
      );
      expect(prefs.themeMode, ThemeMode.system);
    });

    test('setThemeMode updates state to dark', () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      await container.read(accessibilityPreferencesProvider.future);
      await container
          .read(accessibilityPreferencesProvider.notifier)
          .setThemeMode(ThemeMode.dark);

      final prefs = await container.read(
        accessibilityPreferencesProvider.future,
      );
      expect(prefs.themeMode, ThemeMode.dark);
    });

    test('setThemeMode persists to SharedPreferences', () async {
      final container = ProviderContainer();
      addTearDown(container.dispose);

      await container.read(accessibilityPreferencesProvider.future);
      await container
          .read(accessibilityPreferencesProvider.notifier)
          .setThemeMode(ThemeMode.light);

      final sp = await SharedPreferences.getInstance();
      expect(sp.getString('pda_theme_mode'), 'light');
    });

    test('loads persisted theme mode on startup', () async {
      SharedPreferences.setMockInitialValues({'pda_theme_mode': 'dark'});

      final container = ProviderContainer();
      addTearDown(container.dispose);

      final prefs = await container.read(
        accessibilityPreferencesProvider.future,
      );
      expect(prefs.themeMode, ThemeMode.dark);
    });

    test('falls back to system for invalid stored value', () async {
      SharedPreferences.setMockInitialValues({'pda_theme_mode': 'invalid'});

      final container = ProviderContainer();
      addTearDown(container.dispose);

      final prefs = await container.read(
        accessibilityPreferencesProvider.future,
      );
      expect(prefs.themeMode, ThemeMode.system);
    });
  });
}
