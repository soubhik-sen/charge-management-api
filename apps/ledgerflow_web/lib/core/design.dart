import 'package:flutter/material.dart';

abstract final class LedgerFlowDesign {
  static const navy = Color(0xFF061A35);
  static const navyLight = Color(0xFF102F54);
  static const teal = Color(0xFF008985);
  static const tealDark = Color(0xFF006D69);
  static const canvas = Color(0xFFF6F8FA);
  static const ink = Color(0xFF101828);
  static const muted = Color(0xFF667085);
  static const border = Color(0xFFD8E0E8);
  static const success = Color(0xFF14804A);
  static const warning = Color(0xFFC86A00);
  static const danger = Color(0xFFB42318);
  static const info = Color(0xFF175CD3);

  static ThemeData get theme {
    final textTheme = ThemeData.light().textTheme.apply(
      fontFamily: 'Manrope',
      bodyColor: ink,
      displayColor: ink,
    );
    return ThemeData(
      useMaterial3: true,
      colorScheme: ColorScheme.fromSeed(
        seedColor: teal,
        primary: teal,
        surface: Colors.white,
        error: danger,
      ),
      scaffoldBackgroundColor: canvas,
      textTheme: textTheme,
      dividerColor: border,
      cardTheme: const CardThemeData(
        color: Colors.white,
        elevation: 0,
        margin: EdgeInsets.zero,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.all(Radius.circular(12)),
          side: BorderSide(color: border),
        ),
      ),
      inputDecorationTheme: const InputDecorationTheme(
        filled: true,
        fillColor: Colors.white,
        border: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(9)),
          borderSide: BorderSide(color: border),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.all(Radius.circular(9)),
          borderSide: BorderSide(color: border),
        ),
        contentPadding: EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      ),
      filledButtonTheme: FilledButtonThemeData(
        style: FilledButton.styleFrom(
          backgroundColor: teal,
          foregroundColor: Colors.white,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: ink,
          padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 15),
          side: const BorderSide(color: border),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(9)),
        ),
      ),
      dataTableTheme: const DataTableThemeData(
        headingTextStyle: TextStyle(fontWeight: FontWeight.w600, color: muted),
        dataTextStyle: TextStyle(fontSize: 13, color: ink),
        headingRowColor: WidgetStatePropertyAll(Color(0xFFF9FAFB)),
        dividerThickness: 1,
      ),
    );
  }
}

class SurfaceCard extends StatelessWidget {
  const SurfaceCard({
    required this.child,
    this.padding = const EdgeInsets.all(18),
    super.key,
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(padding: padding, child: child),
  );
}

class StatusPill extends StatelessWidget {
  const StatusPill(this.value, {super.key});

  final String value;

  @override
  Widget build(BuildContext context) {
    final normalized = value.toUpperCase();
    final (color, background) = switch (normalized) {
      'APPROVED' ||
      'MATCHED' ||
      'PUBLISHED' ||
      'ACTIVE' ||
      'AWARDED' => (LedgerFlowDesign.success, const Color(0xFFE7F6EC)),
      'REJECTED' ||
      'REVERSED' ||
      'EXCEPTION' ||
      'OUTSIDE TOLERANCE' => (LedgerFlowDesign.danger, const Color(0xFFFFE9E7)),
      'REVIEW' ||
      'RATED' ||
      'RANKED' => (LedgerFlowDesign.info, const Color(0xFFE8F1FF)),
      'DRAFT' ||
      'CAPTURED' => (LedgerFlowDesign.muted, const Color(0xFFF0F2F5)),
      _ => (LedgerFlowDesign.warning, const Color(0xFFFFF1D8)),
    };
    return DecoratedBox(
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(999),
      ),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
        child: Text(
          value.replaceAll('_', ' '),
          style: TextStyle(
            color: color,
            fontSize: 12,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
    );
  }
}
