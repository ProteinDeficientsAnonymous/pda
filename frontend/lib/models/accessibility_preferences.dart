import 'package:flutter/material.dart';
import 'package:freezed_annotation/freezed_annotation.dart';

part 'accessibility_preferences.freezed.dart';

@freezed
abstract class AccessibilityPreferences with _$AccessibilityPreferences {
  const factory AccessibilityPreferences({
    @Default(false) bool dyslexiaFriendlyFont,
    // 1.0 = normal, 1.15 = medium, 1.3 = large
    @Default(1.0) double textScaleFactor,
    @Default(ThemeMode.system) ThemeMode themeMode,
  }) = _AccessibilityPreferences;
}
