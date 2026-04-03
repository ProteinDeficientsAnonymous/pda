import 'package:pda/models/accessibility_preferences.dart';
import 'package:riverpod_annotation/riverpod_annotation.dart';
import 'package:shared_preferences/shared_preferences.dart';

part 'accessibility_preferences_provider.g.dart';

const _keyDyslexiaFont = 'pda_dyslexia_font';
const _keyTextScale = 'pda_text_scale';

@Riverpod(keepAlive: true)
class AccessibilityPreferencesNotifier
    extends _$AccessibilityPreferencesNotifier {
  @override
  Future<AccessibilityPreferences> build() async {
    final prefs = await SharedPreferences.getInstance();
    return AccessibilityPreferences(
      dyslexiaFriendlyFont: prefs.getBool(_keyDyslexiaFont) ?? false,
      textScaleFactor: prefs.getDouble(_keyTextScale) ?? 1.0,
    );
  }

  Future<void> toggleDyslexiaFont() async {
    final current = state.value ?? const AccessibilityPreferences();
    final next = current.copyWith(
      dyslexiaFriendlyFont: !current.dyslexiaFriendlyFont,
    );
    state = AsyncData(next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setBool(_keyDyslexiaFont, next.dyslexiaFriendlyFont);
  }

  Future<void> setTextScale(double scale) async {
    final current = state.value ?? const AccessibilityPreferences();
    final next = current.copyWith(textScaleFactor: scale);
    state = AsyncData(next);
    final prefs = await SharedPreferences.getInstance();
    await prefs.setDouble(_keyTextScale, scale);
  }
}
