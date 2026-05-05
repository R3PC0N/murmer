import 'package:flutter/material.dart';

class AppTheme {
  static const _primary = Color(0xFFC8922A);      // amber — matches logo + landing page
  static const _background = Color(0xFF1C1C1E);   // iOS-grey dark
  static const _surface = Color(0xFF242426);       // raised surface
  static const _surfaceVariant = Color(0xFF2C2C2E); // inputs / cards

  static ThemeData get dark => ThemeData(
        useMaterial3: true,
        brightness: Brightness.dark,
        colorScheme: ColorScheme.dark(
          primary: _primary,
          onPrimary: const Color(0xFF1C1C1E),  // dark text on amber — better contrast
          surface: _surface,
          surfaceContainerHighest: _surfaceVariant,
          onSurface: Colors.white,
        ),
        scaffoldBackgroundColor: _background,
        cardColor: _surface,
        cardTheme: CardThemeData(
          color: _surface,
          elevation: 0,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(12),
          ),
        ),
        appBarTheme: const AppBarTheme(
          backgroundColor: _surface,
          foregroundColor: Colors.white,
          elevation: 0,
          centerTitle: false,
        ),
        listTileTheme: const ListTileThemeData(
          contentPadding: EdgeInsets.symmetric(horizontal: 16, vertical: 2),
        ),
        inputDecorationTheme: InputDecorationTheme(
          filled: true,
          fillColor: _surfaceVariant,
          border: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: BorderSide.none,
          ),
          focusedBorder: OutlineInputBorder(
            borderRadius: BorderRadius.circular(10),
            borderSide: const BorderSide(color: _primary, width: 1.5),
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
              states.contains(WidgetState.selected) ? _primary : Colors.grey),
        ),
      );
}
