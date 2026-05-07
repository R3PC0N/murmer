import 'package:flutter/material.dart';

class AppTheme {
  // ── Dark palette — iOS-grey + amber (matches landing page dark mode) ──────
  static const _primaryDark   = Color(0xFFC8922A);  // amber
  static const _bgDark        = Color(0xFF1C1C1E);  // iOS-grey dark
  static const _surfaceDark   = Color(0xFF242426);  // raised surface
  static const _surfaceVarDark= Color(0xFF2C2C2E);  // inputs / cards

  // ── Light palette — from landing page @media (prefers-color-scheme: light)
  static const _primaryLight  = Color(0xFFA87520);  // darker amber (contrast on white)
  static const _bgLight       = Color(0xFFF2F2F7);  // --bg
  static const _surfaceLight  = Color(0xFFFFFFFF);  // --bg-raised / --surface
  static const _surfaceVarLight= Color(0xFFE5E5EA); // --code-bg (input fill)

  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.dark(
          primary: _primaryDark,
          onPrimary: _bgDark,   // dark text on amber — better contrast
          surface: _surfaceDark,
          surfaceContainerHighest: _surfaceVarDark,
          onSurface: Colors.white,
        ),
        scaffoldBackgroundColor: _bgDark,
        cardColor: _surfaceDark,
        cardTheme: CardThemeData(
          color: _surfaceDark,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: _surfaceDark,
          foregroundColor: Colors.white,
          elevation: 0,
          centerTitle: false,
        ),
        listTileTheme: const ListTileThemeData(
          contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 2),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _surfaceVarDark,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide.none,
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: _primaryDark, width: 1.5),
          ),
          labelStyle: const TextStyle(color: Colors.white60),
        ),
        dividerTheme: const DividerThemeData(
          color: Color(0xFF48484A),  // iOS system separator grey
          thickness: 1,
          indent: 16,
          endIndent: 16,
        ),
        switchTheme: SwitchThemeData(
          thumbColor: WidgetStateProperty.resolveWith((states) =>
              states.contains(WidgetState.selected) ? _primaryDark : Colors.grey),
        ),
      );

  static ThemeData get light => ThemeData(
        useMaterial3: true,
        brightness: Brightness.light,
        colorScheme: ColorScheme.light(
          primary: _primaryLight,
          onPrimary: Colors.white,  // white text on dark amber
          surface: _surfaceLight,
          surfaceContainerHighest: _surfaceVarLight,
          onSurface: const Color(0xFF1C1C1E),
        ),
        scaffoldBackgroundColor: _bgLight,
        cardColor: _surfaceLight,
        cardTheme: CardThemeData(
          color: _surfaceLight,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: _surfaceLight,
          foregroundColor: Color(0xFF1C1C1E),
          elevation: 0,
          centerTitle: false,
        ),
        listTileTheme: const ListTileThemeData(
          contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 2),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _surfaceVarLight,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide.none,
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: _primaryLight, width: 1.5),
          ),
          labelStyle: const TextStyle(color: Color(0xFF6C6C70)),
        ),
        dividerTheme: const DividerThemeData(
          color: Color(0xFFC6C6C8),  // --border light
          thickness: 1,
          indent: 16,
          endIndent: 16,
        ),
        switchTheme: SwitchThemeData(
          thumbColor: WidgetStateProperty.resolveWith((states) =>
              states.contains(WidgetState.selected) ? _primaryLight : Colors.grey),
        ),
      );
}
