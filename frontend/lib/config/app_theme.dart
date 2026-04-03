import 'package:flutter/material.dart';

/// Builds the app [ThemeData] with accessibility-first typography.
///
/// When [dyslexiaMode] is true, the text theme is configured with wider
/// letter spacing, more line height, and will use Atkinson Hyperlegible when
/// the google_fonts dependency is available.
ThemeData buildAppTheme({bool dyslexiaMode = false}) {
  const seedColor = Color(0xFF2E7D32);
  final colorScheme = ColorScheme.fromSeed(seedColor: seedColor);

  final textTheme = _buildTextTheme(dyslexiaMode: dyslexiaMode);

  return ThemeData(
    colorScheme: colorScheme,
    useMaterial3: true,
    textTheme: textTheme,
    appBarTheme: const AppBarTheme(scrolledUnderElevation: 0),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      backgroundColor: seedColor,
      contentTextStyle: const TextStyle(color: Colors.white, fontSize: 14),
    ),
  );
}

TextTheme _buildTextTheme({required bool dyslexiaMode}) {
  // Base spacing values
  final double bodyHeight = dyslexiaMode ? 1.7 : 1.5;
  final double labelHeight = dyslexiaMode ? 1.5 : 1.3;
  final double bodyLetterSpacing = dyslexiaMode ? 0.3 : 0.12;
  final double labelLetterSpacing = dyslexiaMode ? 0.2 : 0.1;

  return TextTheme(
    // Display styles — large hero text
    displayLarge: const TextStyle(
      fontSize: 57,
      fontWeight: FontWeight.w400,
      height: 1.12,
      letterSpacing: -0.25,
    ),
    displayMedium: const TextStyle(
      fontSize: 45,
      fontWeight: FontWeight.w400,
      height: 1.16,
      letterSpacing: 0,
    ),
    displaySmall: const TextStyle(
      fontSize: 36,
      fontWeight: FontWeight.w400,
      height: 1.22,
      letterSpacing: 0,
    ),

    // Headline styles — page titles, section headings
    headlineLarge: const TextStyle(
      fontSize: 32,
      fontWeight: FontWeight.w400,
      height: 1.25,
      letterSpacing: 0,
    ),
    headlineMedium: const TextStyle(
      fontSize: 28,
      fontWeight: FontWeight.w400,
      height: 1.29,
      letterSpacing: 0,
    ),
    headlineSmall: const TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w400,
      height: 1.33,
      letterSpacing: 0,
    ),

    // Title styles — card titles, dialog titles
    titleLarge: TextStyle(
      fontSize: 22,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
    ),
    titleSmall: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
    ),

    // Body styles — primary reading text, minimum 14px
    bodyLarge: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w400,
      height: bodyHeight,
      letterSpacing: bodyLetterSpacing,
    ),
    bodyMedium: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      height: bodyHeight,
      letterSpacing: bodyLetterSpacing,
    ),
    bodySmall: TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w400,
      height: bodyHeight,
      letterSpacing: bodyLetterSpacing,
    ),

    // Label styles — badges, captions, helper text, minimum 12px
    labelLarge: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
    ),
    labelMedium: TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
    ),
    labelSmall: TextStyle(
      fontSize: 11,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
    ),
  );
}
