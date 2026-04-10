import 'package:flutter/material.dart';

/// Builds the app [ThemeData] with accessibility-first typography.
///
/// When [dyslexiaMode] is true, the text theme switches to OpenDyslexic and
/// is configured with wider letter spacing and more line height.
ThemeData buildAppTheme({
  bool dyslexiaMode = false,
  Brightness brightness = Brightness.light,
}) {
  const seedColor = Color(0xFF2E7D32);
  final colorScheme = ColorScheme.fromSeed(
    seedColor: seedColor,
    brightness: brightness,
  );
  final String? fontFamily = dyslexiaMode ? 'OpenDyslexic' : null;

  final textTheme = _buildTextTheme(
    dyslexiaMode: dyslexiaMode,
    fontFamily: fontFamily,
  );

  final inputBorder = OutlineInputBorder(
    borderRadius: BorderRadius.circular(12),
  );

  return ThemeData(
    colorScheme: colorScheme,
    useMaterial3: true,
    textTheme: textTheme,
    appBarTheme: const AppBarTheme(scrolledUnderElevation: 0),
    dialogTheme: DialogThemeData(
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
    ),
    inputDecorationTheme: InputDecorationTheme(
      border: inputBorder,
      enabledBorder: inputBorder,
      focusedBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colorScheme.primary, width: 2),
      ),
      errorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colorScheme.error),
      ),
      focusedErrorBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(12),
        borderSide: BorderSide(color: colorScheme.error, width: 2),
      ),
      contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
    ),
    pageTransitionsTheme: PageTransitionsTheme(
      builders: {
        for (final platform in TargetPlatform.values)
          platform: const _NoTransitionBuilder(),
      },
    ),
    snackBarTheme: SnackBarThemeData(
      behavior: SnackBarBehavior.floating,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      backgroundColor: colorScheme.inverseSurface,
      contentTextStyle: TextStyle(
        color: colorScheme.onInverseSurface,
        fontSize: 14,
        fontFamily: fontFamily,
      ),
    ),
  );
}

TextTheme _buildTextTheme({required bool dyslexiaMode, String? fontFamily}) {
  // Base spacing values
  final double bodyHeight = dyslexiaMode ? 1.7 : 1.5;
  final double labelHeight = dyslexiaMode ? 1.5 : 1.3;
  final double bodyLetterSpacing = dyslexiaMode ? 0.3 : 0.12;
  final double labelLetterSpacing = dyslexiaMode ? 0.2 : 0.1;

  return TextTheme(
    // Display styles — large hero text
    displayLarge: TextStyle(
      fontSize: 57,
      fontWeight: FontWeight.w400,
      height: 1.12,
      letterSpacing: -0.25,
      fontFamily: fontFamily,
    ),
    displayMedium: TextStyle(
      fontSize: 45,
      fontWeight: FontWeight.w400,
      height: 1.16,
      letterSpacing: 0,
      fontFamily: fontFamily,
    ),
    displaySmall: TextStyle(
      fontSize: 36,
      fontWeight: FontWeight.w400,
      height: 1.22,
      letterSpacing: 0,
      fontFamily: fontFamily,
    ),

    // Headline styles — page titles, section headings
    headlineLarge: TextStyle(
      fontSize: 32,
      fontWeight: FontWeight.w400,
      height: 1.25,
      letterSpacing: 0,
      fontFamily: fontFamily,
    ),
    headlineMedium: TextStyle(
      fontSize: 28,
      fontWeight: FontWeight.w400,
      height: 1.29,
      letterSpacing: 0,
      fontFamily: fontFamily,
    ),
    headlineSmall: TextStyle(
      fontSize: 24,
      fontWeight: FontWeight.w400,
      height: 1.33,
      letterSpacing: 0,
      fontFamily: fontFamily,
    ),

    // Title styles — card titles, dialog titles
    titleLarge: TextStyle(
      fontSize: 22,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
      fontFamily: fontFamily,
    ),
    titleMedium: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
      fontFamily: fontFamily,
    ),
    titleSmall: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
      fontFamily: fontFamily,
    ),

    // Body styles — primary reading text, minimum 14px
    bodyLarge: TextStyle(
      fontSize: 16,
      fontWeight: FontWeight.w400,
      height: bodyHeight,
      letterSpacing: bodyLetterSpacing,
      fontFamily: fontFamily,
    ),
    bodyMedium: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w400,
      height: bodyHeight,
      letterSpacing: bodyLetterSpacing,
      fontFamily: fontFamily,
    ),
    bodySmall: TextStyle(
      fontSize: 13,
      fontWeight: FontWeight.w400,
      height: bodyHeight,
      letterSpacing: bodyLetterSpacing,
      fontFamily: fontFamily,
    ),

    // Label styles — badges, captions, helper text, minimum 12px
    labelLarge: TextStyle(
      fontSize: 14,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
      fontFamily: fontFamily,
    ),
    labelMedium: TextStyle(
      fontSize: 12,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
      fontFamily: fontFamily,
    ),
    labelSmall: TextStyle(
      fontSize: 11,
      fontWeight: FontWeight.w500,
      height: labelHeight,
      letterSpacing: labelLetterSpacing,
      fontFamily: fontFamily,
    ),
  );
}

class _NoTransitionBuilder extends PageTransitionsBuilder {
  const _NoTransitionBuilder();

  @override
  Widget buildTransitions<T>(
    PageRoute<T> route,
    BuildContext context,
    Animation<double> animation,
    Animation<double> secondaryAnimation,
    Widget child,
  ) {
    return FadeTransition(
      opacity: CurvedAnimation(parent: animation, curve: Curves.easeOut),
      child: child,
    );
  }
}
