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
const _bg            = Color(0xFF1A1A1A);
const _borderIdle    = Color(0xFF666666);
const _borderRec     = Color(0xFFFF3B30);
const _borderProc    = Color(0xFFD4930A);
const _borderSuccess = Color(0xFF34C759);
const _borderError   = Color(0xFFFF3B30);

const _iconIdle    = Color(0xFFCCCCCC);
const _iconRec     = Color(0xFFFF3B30);
const _iconProc    = Color(0xFFD4930A);
const _iconSuccess = Color(0xFF34C759);
const _iconError   = Color(0xFFFF3B30);

const _size   = 58.0;
const _radius = 14.0;

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
      duration: const Duration(milliseconds: 1200),
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

        const ch = MethodChannel('com.murmer/clipboard');
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
      File('/data/user/0/com.murmer.mobile/cache/murmer_debug.txt')
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
            padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 14),
            child: LayoutBuilder(
              builder: (_, constraints) => CustomPaint(
                size: Size(constraints.maxWidth, constraints.maxHeight),
                painter: _SineWavePainter(
                  phase: _phaseAnim.value,
                  color: iconColor,
                  speed: switch (_state) {
                    _MicState.recording  => 1.0,
                    _MicState.processing => 0.3,
                    _                   => 0.0,
                  },
                ),
              ),
            ),
          ),
      },
    );
  }
}

// ── Sine wave painter ──────────────────────────────────────────────────────

class _SineWavePainter extends CustomPainter {
  /// 0→1 animation phase (from AnimationController)
  final double phase;

  /// 0 = static, 1 = full scroll speed
  final double speed;

  final Color color;

  const _SineWavePainter({
    required this.phase,
    required this.speed,
    required this.color,
  });

  @override
  void paint(Canvas canvas, Size size) {
    final paint = Paint()
      ..color = color
      ..strokeWidth = 2.5
      ..style = PaintingStyle.stroke
      ..strokeCap = StrokeCap.round
      ..strokeJoin = StrokeJoin.round;

    final centerY  = size.height / 2;
    final amplitude = size.height * 0.38;

    // How many full cycles across the width (1.5 looks like the screenshot)
    const cycles = 1.5;

    // Horizontal scroll offset driven by phase * speed
    final offset = phase * speed;

    final path = Path();
    const steps = 120; // sample points for smooth curve

    for (int i = 0; i <= steps; i++) {
      final t = i / steps; // 0→1 across width
      final x = t * size.width;
      final radians = (t * cycles + offset) * 2 * math.pi;
      final y = centerY - amplitude * math.sin(radians);

      if (i == 0) {
        path.moveTo(x, y);
      } else {
        path.lineTo(x, y);
      }
    }

    canvas.drawPath(path, paint);
  }

  @override
  bool shouldRepaint(_SineWavePainter old) =>
      old.phase != phase || old.color != color || old.speed != speed;
}
