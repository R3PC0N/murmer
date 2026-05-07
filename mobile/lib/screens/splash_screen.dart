import 'dart:math' as math;
import 'package:flutter/material.dart';

import 'home_screen.dart';

/// Flutter-level animated splash screen.
///
/// Shown as the app's first route, immediately after Flutter initialises.
/// Plays the 7-bar waveform animation (matching the website / landing page)
/// for [_duration], then fades into [HomeScreen].
class SplashScreen extends StatefulWidget {
  const SplashScreen({super.key});

  @override
  State<SplashScreen> createState() => _SplashScreenState();
}

class _SplashScreenState extends State<SplashScreen>
    with SingleTickerProviderStateMixin {
  static const _duration   = Duration(milliseconds: 2000); // one full wave cycle
  static const _holdFor    = Duration(milliseconds: 1600); // show before navigating
  static const _fadeDur    = Duration(milliseconds: 400);

  late final AnimationController _ctrl;

  @override
  void initState() {
    super.initState();
    _ctrl = AnimationController(vsync: this, duration: _duration)..repeat();
    Future.delayed(_holdFor, _navigate);
  }

  void _navigate() {
    if (!mounted) return;
    Navigator.of(context).pushReplacement(
      PageRouteBuilder(
        pageBuilder: (_, __, ___) => const HomeScreen(),
        transitionsBuilder: (_, anim, __, child) =>
            FadeTransition(opacity: anim, child: child),
        transitionDuration: _fadeDur,
      ),
    );
  }

  @override
  void dispose() {
    _ctrl.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final color = Theme.of(context).colorScheme.primary;
    return Scaffold(
      // Matches app background so the transition from native splash is seamless.
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: Center(
        child: AnimatedBuilder(
          animation: _ctrl,
          builder: (_, __) => CustomPaint(
            size: const Size(96, 64),
            painter: _SplashWaveformPainter(phase: _ctrl.value, color: color),
          ),
        ),
      ),
    );
  }
}

// ── Waveform painter — same proportions as the logo / mic overlay ─────────

class _SplashWaveformPainter extends CustomPainter {
  final double phase;
  final Color  color;

  const _SplashWaveformPainter({required this.phase, required this.color});

  // Identical to the website CSS animation delays (converted to fractions of 1).
  static const _ratios = [0.25, 0.45, 0.65, 0.85, 0.65, 0.45, 0.25];
  // delay / 2s (website: 0s, 0.18s, 0.36s, 0.54s) — centre bar leads.
  static const _delays = [0.00, 0.09, 0.18, 0.27, 0.18, 0.09, 0.00];

  @override
  void paint(Canvas canvas, Size size) {
    const n    = 7;
    final barW = size.width * 0.11;
    final gap  = (size.width - n * barW) / (n - 1);
    final cy   = size.height / 2;
    final r    = barW / 2;

    for (int i = 0; i < n; i++) {
      // Each bar breathes with a staggered sine, matching the landing page.
      final t    = ((phase - _delays[i]) % 1.0 + 1.0) % 1.0;
      final sine = math.sin(t * 2 * math.pi); // −1 → +1
      // Map to [0.4, 1.0] like the CSS animation (scaleY 0.4 → 1).
      final scaleY = 0.4 + 0.6 * (sine * 0.5 + 0.5);
      final opacity = 0.4 + 0.6 * (sine * 0.5 + 0.5);

      final h = (size.height * _ratios[i] * scaleY).clamp(2.0, size.height);
      final x = i * (barW + gap);
      final y = cy - h / 2;

      final paint = Paint()
        ..color  = color.withOpacity(opacity)
        ..style  = PaintingStyle.fill;

      canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(x, y, barW, h), Radius.circular(r)),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_SplashWaveformPainter old) =>
      old.phase != phase || old.color != color;
}
