import 'dart:async';
import 'dart:io';
import 'dart:math' as math;
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:http/http.dart' as http;
import 'package:permission_handler/permission_handler.dart';

import '../services/audio_service.dart';
import '../services/whisper_service.dart';
import '../services/storage_service.dart';

enum _MicState { idle, recording, processing, success, error }

// ── Design tokens ──────────────────────────────────────────────────────────
const _bg            = Color(0xFF1C1C1E);  // matches app background
const _borderIdle    = Color(0xFF48484A);  // iOS system separator grey
const _borderRec     = Color(0xFFFF3B30);  // red — semantic, unchanged
const _borderProc    = Color(0xFFC8922A);  // amber — matches logo
const _borderSuccess = Color(0xFF34C759);  // green — semantic, unchanged
const _borderError   = Color(0xFFFF3B30);  // red — semantic, unchanged

const _iconIdle    = Color(0xFF8E8E93);  // iOS system grey (muted)
const _iconRec     = Color(0xFFFF3B30);  // red — semantic, unchanged
const _iconProc    = Color(0xFFC8922A);  // amber — matches logo
const _iconSuccess = Color(0xFF34C759);  // green — semantic, unchanged
const _iconError   = Color(0xFFFF3B30);  // red — semantic, unchanged

const _size   = 68.0;
const _radius = 16.0;

class MicButtonOverlay extends StatefulWidget {
  const MicButtonOverlay({super.key});

  @override
  State<MicButtonOverlay> createState() => _MicButtonOverlayState();
}

class _MicButtonOverlayState extends State<MicButtonOverlay>
    with SingleTickerProviderStateMixin {
  final _audio   = AudioService();
  final _whisper = WhisperService();
  final _storage = StorageService.instance;

  _MicState _state    = _MicState.idle;
  String    _errorMsg = '';

  // Single controller: drives wave scroll + border pulse
  late AnimationController _animCtrl;
  late Animation<double>   _phaseAnim;   // 0→1 repeating, for wave offset
  late Animation<double>   _pulseAnim;   // 0.4→1.0 for border opacity pulse

  @override
  void initState() {
    super.initState();
    _initStorage();

    _animCtrl = AnimationController(
      vsync: this,
      duration: const Duration(milliseconds: 2000), // matches landing page 2s wave
    )..repeat();

    // Phase: drives horizontal wave scroll
    _phaseAnim = Tween<double>(begin: 0.0, end: 1.0).animate(_animCtrl);

    // Border pulse: sine curve mapped to opacity
    _pulseAnim = _animCtrl.drive(
      Tween<double>(begin: 0.4, end: 1.0).chain(
        CurveTween(curve: Curves.easeInOut),
      ),
    );
  }

  Future<void> _initStorage() async => await _storage.init();

  @override
  void dispose() {
    _animCtrl.dispose();
    _audio.dispose();
    super.dispose();
  }

  // ── Tap ──────────────────────────────────────────────────────────────────

  Future<void> _onTap() async {
    if (_state == _MicState.recording) {
      await _stopAndTranscribe();
    } else if (_state == _MicState.idle) {
      await _startRecording();
    }
  }

  // ── Recording ────────────────────────────────────────────────────────────

  Future<void> _startRecording() async {
    if (!await Permission.microphone.status.then((s) => s.isGranted)) {
      _flashError('Mic\ndenied');
      return;
    }
    await _audio.startRecording();
    setState(() => _state = _MicState.recording);
  }

  // ── Transcription ────────────────────────────────────────────────────────

  Future<void> _stopAndTranscribe() async {
    setState(() => _state = _MicState.processing);
    _log('--- stopAndTranscribe ---');

    final file = await _audio.stopRecording();
    _log('audio: ${file?.path} size=${file?.lengthSync()}');

    if (file == null) { _flashError('No audio'); return; }

    // Reload from disk — overlay engine may cache stale SharedPreferences
    await _storage.init();
    final server = _storage.getActiveServer();
    if (server == null) { _flashError('No server'); return; }

    try {
      await http.get(
        Uri.parse('${server.url}/health'),
        headers: {'X-API-Key': server.apiKey},
      ).timeout(const Duration(seconds: 10));
    } catch (e) {
      _log('health failed: $e');
      _flashError('No\nconn.');
      return;
    }

    try {
      final result = await _whisper.transcribe(
        server, file,
        profile: _storage.getActiveProfile(),
        anthropicKey: _storage.getAnthropicKey(),
        aiCleanup: _storage.isAiCleanupEnabled(),
      );
      _log('result: "${result.text}"');

      if (result.text.isNotEmpty) {
        setState(() => _state = _MicState.success);

        const ch = MethodChannel('com.murmur/clipboard');
        ch.invokeMethod('pasteText', {'text': result.text})
            .then((_) => _log('paste triggered'))
            .catchError((e) => _log('paste error: $e'));

        Future.delayed(const Duration(milliseconds: 1500),
            () { if (mounted) setState(() => _state = _MicState.idle); });
      } else {
        _flashError('Empty');
      }
    } catch (e) {
      _log('error: $e');
      _flashError('Error');
    }
  }

  void _flashError(String msg) {
    setState(() { _state = _MicState.error; _errorMsg = msg; });
    Future.delayed(const Duration(seconds: 2),
        () { if (mounted) setState(() => _state = _MicState.idle); });
  }

  void _log(String msg) {
    try {
      File('/data/user/0/com.murmur.mobile/cache/murmur_debug.txt')
          .writeAsStringSync('${DateTime.now().toIso8601String()} $msg\n',
              mode: FileMode.append);
    } catch (_) {}
  }

  // ── Build ────────────────────────────────────────────────────────────────

  @override
  Widget build(BuildContext context) {
    return Material(
      color: Colors.transparent,
      child: GestureDetector(
        onTap: _onTap,
        child: AnimatedBuilder(
          animation: _animCtrl,
          builder: (_, __) => _buildButton(),
        ),
      ),
    );
  }

  Widget _buildButton() {
    final Color borderColor = switch (_state) {
      _MicState.idle       => _borderIdle,
      _MicState.recording  => _borderRec.withOpacity(_pulseAnim.value),
      _MicState.processing => _borderProc,
      _MicState.success    => _borderSuccess,
      _MicState.error      => _borderError,
    };

    final Color iconColor = switch (_state) {
      _MicState.idle       => _iconIdle,
      _MicState.recording  => _iconRec,
      _MicState.processing => _iconProc,
      _MicState.success    => _iconSuccess,
      _MicState.error      => _iconError,
    };

    return AnimatedContainer(
      duration: const Duration(milliseconds: 200),
      width: _size,
      height: _size,
      decoration: BoxDecoration(
        color: _bg,
        borderRadius: BorderRadius.circular(_radius),
        border: Border.all(color: borderColor, width: 1.5),
      ),
      child: switch (_state) {
        _MicState.error => Center(
            child: Text(
              _errorMsg,
              textAlign: TextAlign.center,
              style: TextStyle(
                color: iconColor,
                fontSize: 9,
                fontWeight: FontWeight.w600,
                height: 1.3,
              ),
            ),
          ),
        _ => Padding(
            padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 10),
            child: LayoutBuilder(
              builder: (_, constraints) => CustomPaint(
                size: Size(constraints.maxWidth, constraints.maxHeight),
                painter: _WaveformPainter(
                  phase: _phaseAnim.value,
                  color: iconColor,
                  // speed: how fast the bars breathe (multiplier on phase)
                  // minScale: lowest bar height as fraction of its natural height
                  speed: switch (_state) {
                    _MicState.recording  => 2.0,  // fast & energetic
                    _MicState.processing => 1.0,  // gentle, like landing page
                    _                   => 0.0,   // static
                  },
                  minScale: switch (_state) {
                    _MicState.recording  => 0.15, // dramatic swing
                    _MicState.processing => 0.40, // subtle breathing
                    _                   => 1.0,   // frozen at natural height
                  },
                ),
              ),
            ),
          ),
      },
    );
  }
}

// ── Waveform painter — 7 bars matching the Murmur logo ───────────────────

class _WaveformPainter extends CustomPainter {
  /// 0→1 animation phase (from AnimationController).
  final double phase;

  /// Bar colour.
  final Color color;

  /// Phase multiplier: 0 = static, 1 = landing-page speed, 2 = fast recording.
  final double speed;

  /// Minimum bar height as a fraction of its natural height (0.15–1.0).
  /// 1.0 means no animation (static at natural height).
  final double minScale;

  const _WaveformPainter({
    required this.phase,
    required this.color,
    this.speed    = 0.0,
    this.minScale = 1.0,
  });

  // Height ratios & stagger delays — identical to the logo and landing page.
  static const _ratios = [0.25, 0.45, 0.65, 0.85, 0.65, 0.45, 0.25];
  // Delays as fractions of one cycle; centre bar leads (delay 0), edges follow.
  static const _delays = [0.54, 0.36, 0.18, 0.00, 0.18, 0.36, 0.54];

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()..color = color..style = PaintingStyle.fill;

    const n = 7;
    // Bar width: ~11 % of available width; gap fills the rest evenly.
    final barW = size.width * 0.11;
    final gap  = (size.width - n * barW) / (n - 1);
    final cy   = size.height / 2;
    final r    = barW / 2;

    for (int i = 0; i < n; i++) {
      double scaleY;
      if (speed == 0.0) {
        scaleY = 1.0; // static — no animation
      } else {
        // Staggered sine: each bar breathes offset from its neighbours.
        final t = ((phase * speed - _delays[i]) % 1.0 + 1.0) % 1.0;
        final sine = math.sin(t * 2 * math.pi); // -1 → +1
        // Map sine to [minScale, 1.0]
        scaleY = minScale + (1.0 - minScale) * (sine * 0.5 + 0.5);
      }

      final h = (size.height * _ratios[i] * scaleY).clamp(2.0, size.height);
      final x = i * (barW + gap);
      final y = cy - h / 2;

      canvas.drawRRect(
        RRect.fromRectAndRadius(Rect.fromLTWH(x, y, barW, h), Radius.circular(r)),
        paint,
      );
    }
  }

  @override
  bool shouldRepaint(_WaveformPainter old) =>
      old.phase != phase || old.color != color ||
      old.speed != speed || old.minScale != minScale;
}
