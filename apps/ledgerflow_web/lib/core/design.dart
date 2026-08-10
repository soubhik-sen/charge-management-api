import 'package:flutter/material.dart';

abstract final class LedgerFlowDesign {
  static const navy = Color(0xFF14213D);
  static const navyLight = Color(0xFF203456);
  static const teal = Color(0xFF0F766E);
  static const tealDark = Color(0xFF0B5F59);
  static const aqua = Color(0xFF1BA6A6);
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

class LedgerFlowLogo extends StatelessWidget {
  const LedgerFlowLogo({
    this.markSize = 38,
    this.fontSize = 20,
    this.onDark = false,
    this.monochrome = false,
    this.showWordmark = true,
    super.key,
  });

  final double markSize;
  final double fontSize;
  final bool onDark;
  final bool monochrome;
  final bool showWordmark;

  @override
  Widget build(BuildContext context) {
    final ledgerColor = onDark ? Colors.white : LedgerFlowDesign.navy;
    final flowColor = monochrome
        ? ledgerColor
        : (onDark ? const Color(0xFF62D5CF) : LedgerFlowDesign.teal);
    return Semantics(
      label: 'LedgerFlow',
      image: true,
      child: ExcludeSemantics(
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            LedgerFlowMark(
              size: markSize,
              foregroundColor: ledgerColor,
              monochrome: monochrome,
            ),
            if (showWordmark) ...[
              SizedBox(width: markSize * 0.22),
              Text.rich(
                TextSpan(
                  children: [
                    TextSpan(
                      text: 'Ledger',
                      style: TextStyle(color: ledgerColor),
                    ),
                    TextSpan(
                      text: 'Flow',
                      style: TextStyle(color: flowColor),
                    ),
                  ],
                ),
                maxLines: 1,
                style: TextStyle(
                  fontFamily: 'Manrope',
                  fontSize: fontSize,
                  fontWeight: FontWeight.w700,
                  letterSpacing: -0.65,
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }
}

class LedgerFlowMark extends StatelessWidget {
  const LedgerFlowMark({
    this.size = 38,
    this.foregroundColor = LedgerFlowDesign.navy,
    this.monochrome = false,
    this.contained = false,
    super.key,
  });

  final double size;
  final Color foregroundColor;
  final bool monochrome;
  final bool contained;

  @override
  Widget build(BuildContext context) => SizedBox.square(
    dimension: size,
    child: CustomPaint(
      painter: _LedgerFlowMarkPainter(
        foregroundColor: foregroundColor,
        monochrome: monochrome,
        contained: contained,
      ),
    ),
  );
}

class _LedgerFlowMarkPainter extends CustomPainter {
  const _LedgerFlowMarkPainter({
    required this.foregroundColor,
    required this.monochrome,
    required this.contained,
  });

  final Color foregroundColor;
  final bool monochrome;
  final bool contained;

  @override
  void paint(Canvas canvas, Size size) {
    final scale = size.width / 64;
    canvas.scale(scale, scale);
    if (contained) {
      canvas.drawRRect(
        RRect.fromRectAndRadius(
          const Rect.fromLTWH(0, 0, 64, 64),
          const Radius.circular(14),
        ),
        Paint()..color = LedgerFlowDesign.navy,
      );
    }
    final primary = contained ? Colors.white : foregroundColor;
    final secondary = monochrome ? primary : LedgerFlowDesign.teal;
    final accent = monochrome ? primary : LedgerFlowDesign.aqua;

    canvas.drawPath(
      Path()
        ..moveTo(12, 10)
        ..lineTo(22, 10)
        ..lineTo(22, 40)
        ..lineTo(33, 40)
        ..lineTo(43, 50)
        ..lineTo(12, 50)
        ..close(),
      Paint()..color = primary,
    );
    canvas.drawRect(
      const Rect.fromLTWH(26, 18, 25, 7),
      Paint()..color = secondary,
    );
    canvas.drawRect(
      const Rect.fromLTWH(26, 29, 25, 7),
      Paint()..color = secondary,
    );
    canvas.drawPath(
      Path()
        ..moveTo(34, 39)
        ..lineTo(46, 39)
        ..lineTo(58, 51)
        ..lineTo(46, 51)
        ..close(),
      Paint()..color = accent,
    );
  }

  @override
  bool shouldRepaint(covariant _LedgerFlowMarkPainter oldDelegate) =>
      foregroundColor != oldDelegate.foregroundColor ||
      monochrome != oldDelegate.monochrome ||
      contained != oldDelegate.contained;
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
