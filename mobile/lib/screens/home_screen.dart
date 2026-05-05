import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_overlay_window/flutter_overlay_window.dart';
import 'package:permission_handler/permission_handler.dart';
import '../models/server_config.dart';
import '../models/profile.dart';
import '../services/storage_service.dart';
import '../services/whisper_service.dart';
import 'settings/settings_screen.dart';
import 'profile/profile_screen.dart';

const _websiteUrl = 'https://murmurlabs.dev';

Future<void> _openWebsite() async {
  try {
    await const MethodChannel('com.murmur/main')
        .invokeMethod('openUrl', {'url': _websiteUrl});
  } catch (_) {}
}

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _storage = StorageService.instance;
  final _whisper = WhisperService();

  static const _accessibilityChannel = MethodChannel('com.murmur/accessibility');
  static const _mainChannel = MethodChannel('com.murmur/main');

  ServerConfig? _activeServer;
  Profile _activeProfile = Profile.defaultProfile;
  bool _overlayActive = false;
  _ServerStatus _serverStatus = _ServerStatus.unknown;
  bool _accessibilityEnabled = false;

  @override
  void initState() {
    super.initState();
    _load();
    _checkBootAutoStart();
  }

  /// If the app was launched by BootReceiver, start the overlay immediately
  /// and move the app to the background so the user doesn't see it.
  Future<void> _checkBootAutoStart() async {
    try {
      final shouldAutoStart =
          await _mainChannel.invokeMethod<bool>('shouldAutoStartOverlay') ?? false;
      if (!shouldAutoStart) return;

      // Give Flutter a moment to finish building before we start the overlay
      await Future.delayed(const Duration(milliseconds: 500));
      await _startOverlayAndBackground();
    } catch (_) {}
  }

  Future<void> _startOverlayAndBackground() async {
    final hasPermission = await FlutterOverlayWindow.isPermissionGranted();
    if (!hasPermission) return;

    final micStatus = await Permission.microphone.status;
    if (!micStatus.isGranted) return;

    await FlutterOverlayWindow.showOverlay(
      enableDrag: true,
      overlayTitle: 'Murmur',
      overlayContent: 'Voice dictation overlay',
      flag: OverlayFlag.defaultFlag,
      visibility: NotificationVisibility.visibilityPublic,
      positionGravity: PositionGravity.none,
      height: 110,
      width: 110,
      startPosition: const OverlayPosition(0, -200),
    );

    // Move app to background — user only sees the overlay, not the app
    try {
      await _mainChannel.invokeMethod('moveToBackground');
    } catch (_) {}
  }

  Future<void> _load() async {
    final server = _storage.getActiveServer();
    final profile = _storage.getActiveProfile();
    final overlayActive = await FlutterOverlayWindow.isActive();
    bool accessibilityEnabled = false;
    try {
      accessibilityEnabled =
          await _accessibilityChannel.invokeMethod('isEnabled') == true;
    } catch (_) {}
    setState(() {
      _activeServer = server;
      _activeProfile = profile;
      _overlayActive = overlayActive;
      _serverStatus = _ServerStatus.unknown;
      _accessibilityEnabled = accessibilityEnabled;
    });
    if (server != null) _checkServer(server);
  }

  Future<void> _openAccessibilitySettings() async {
    try {
      await _accessibilityChannel.invokeMethod('openSettings');
    } catch (_) {}
  }

  Future<void> _checkServer(ServerConfig server) async {
    setState(() => _serverStatus = _ServerStatus.checking);
    try {
      await _whisper.checkHealth(server);
      if (mounted) setState(() => _serverStatus = _ServerStatus.ok);
    } catch (_) {
      if (mounted) setState(() => _serverStatus = _ServerStatus.error);
    }
  }

  Future<void> _toggleOverlay() async {
    if (_activeServer == null) {
      _showSnack('Configure a server first.');
      return;
    }

    if (_overlayActive) {
      await FlutterOverlayWindow.closeOverlay();
      setState(() => _overlayActive = false);
    } else {
      final hasPermission = await FlutterOverlayWindow.isPermissionGranted();
      if (!hasPermission) {
        await FlutterOverlayWindow.requestPermission();
        return;
      }
      // Android 14+ requires RECORD_AUDIO to be granted before starting a
      // foreground service with foregroundServiceType="microphone".
      final micStatus = await Permission.microphone.request();
      if (!micStatus.isGranted) {
        _showSnack('Microphone permission is required for the overlay.');
        return;
      }
      await FlutterOverlayWindow.showOverlay(
        enableDrag: true,
        overlayTitle: 'Murmur',
        overlayContent: 'Voice dictation overlay',
        flag: OverlayFlag.defaultFlag,
        visibility: NotificationVisibility.visibilityPublic,
        positionGravity: PositionGravity.none,
        height: 90,
        width: 90,
        startPosition: const OverlayPosition(0, -200),
      );
      setState(() => _overlayActive = true);
    }
  }

  void _showSnack(String msg) {
    ScaffoldMessenger.of(context).showSnackBar(SnackBar(content: Text(msg)));
  }

  Future<void> _openSettings() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const SettingsScreen()),
    );
    _load();
  }

  Future<void> _openProfiles() async {
    await Navigator.push(
      context,
      MaterialPageRoute(builder: (_) => const ProfileScreen()),
    );
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    return Scaffold(
      appBar: AppBar(
        title: const Text('Murmur'),
        actions: [
          IconButton(
            icon: const Icon(Icons.settings_outlined),
            onPressed: _openSettings,
            tooltip: 'Settings',
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Server status card
            _StatusCard(
              label: 'Server',
              value: _activeServer?.name ?? 'Not configured',
              subtitle: _activeServer?.displayUrl,
              status: _serverStatus,
              onTap: _openSettings,
            ),
            const SizedBox(height: 12),

            // Active profile card
            _StatusCard(
              label: 'Profile',
              value: _activeProfile.name,
              subtitle: _activeProfile.style.label,
              status: _ServerStatus.ok,
              statusIcon: Icons.person_outline,
              onTap: _openProfiles,
            ),
            const SizedBox(height: 12),

            // Accessibility service card
            _AccessibilityCard(
              enabled: _accessibilityEnabled,
              onEnable: () async {
                await _openAccessibilitySettings();
                // Re-check after returning from settings
                await Future.delayed(const Duration(milliseconds: 500));
                _load();
              },
            ),
            const SizedBox(height: 32),

            // Overlay toggle
            Center(
              child: Column(
                children: [
                  GestureDetector(
                    onTap: _toggleOverlay,
                    child: AnimatedContainer(
                      duration: const Duration(milliseconds: 300),
                      width: 120,
                      height: 120,
                      decoration: BoxDecoration(
                        shape: BoxShape.circle,
                        color: _overlayActive
                            ? cs.primary
                            : cs.surfaceContainerHighest,
                        boxShadow: _overlayActive
                            ? [
                                BoxShadow(
                                  color: cs.primary.withOpacity(0.4),
                                  blurRadius: 24,
                                  spreadRadius: 4,
                                )
                              ]
                            : [],
                      ),
                      child: Icon(
                        _overlayActive ? Icons.mic : Icons.mic_off,
                        size: 52,
                        color: _overlayActive ? Colors.white : cs.onSurface,
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),
                  Text(
                    _overlayActive ? 'Overlay active' : 'Overlay off',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 6),
                  Text(
                    _overlayActive
                        ? 'Floating mic button is visible in all apps'
                        : 'Tap to enable the floating mic button',
                    style: Theme.of(context)
                        .textTheme
                        .bodySmall
                        ?.copyWith(color: cs.onSurfaceVariant),
                    textAlign: TextAlign.center,
                  ),
                ],
              ),
            ),
            const SizedBox(height: 40),

            // Setup card (no server) OR quick tips (server configured, overlay off)
            if (_activeServer == null) ...[
              const _SetupCard(),
              const SizedBox(height: 8),
            ] else if (!_overlayActive) ...[
              _TipCard(
                icon: Icons.swipe,
                text: 'Enable the overlay, then switch to any app. '
                    'Tap the floating mic button to start dictating.',
              ),
              const SizedBox(height: 8),
              _TipCard(
                icon: Icons.content_paste_go,
                text: 'After recording, your transcription is automatically '
                    'pasted into the focused text field. Enable the '
                    'Accessibility service above for this to work.',
              ),
              const SizedBox(height: 8),
            ],

            // Footer — always visible
            const _Footer(),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
  }
}

// ── Supporting widgets ─────────────────────────────────────────────────────

enum _ServerStatus { unknown, checking, ok, error }

class _StatusCard extends StatelessWidget {
  final String label;
  final String value;
  final String? subtitle;
  final _ServerStatus status;
  final IconData? statusIcon;
  final VoidCallback? onTap;

  const _StatusCard({
    required this.label,
    required this.value,
    this.subtitle,
    required this.status,
    this.statusIcon,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;

    Widget indicator;
    if (statusIcon != null) {
      indicator = Icon(statusIcon, size: 18, color: cs.primary);
    } else {
      indicator = switch (status) {
        _ServerStatus.checking => const SizedBox(
            width: 14,
            height: 14,
            child: CircularProgressIndicator(strokeWidth: 2),
          ),
        _ServerStatus.ok => Icon(Icons.check_circle, size: 18, color: Colors.green[400]),
        _ServerStatus.error => Icon(Icons.error_outline, size: 18, color: Colors.red[400]),
        _ServerStatus.unknown => Icon(Icons.circle_outlined, size: 18, color: cs.outline),
      };
    }

    return Card(
      child: ListTile(
        onTap: onTap,
        leading: indicator,
        title: Text(value, style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: subtitle != null ? Text(subtitle!) : null,
        trailing: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(label,
                style: Theme.of(context)
                    .textTheme
                    .labelSmall
                    ?.copyWith(color: cs.onSurfaceVariant)),
            const SizedBox(width: 4),
            const Icon(Icons.chevron_right, size: 18),
          ],
        ),
      ),
    );
  }
}

class _AccessibilityCard extends StatelessWidget {
  final bool enabled;
  final VoidCallback onEnable;

  const _AccessibilityCard({required this.enabled, required this.onEnable});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Card(
      color: enabled
          ? cs.surfaceContainerHighest
          : Colors.orange.withOpacity(0.12),
      child: ListTile(
        leading: Icon(
          enabled ? Icons.accessibility_new : Icons.warning_amber_rounded,
          color: enabled ? Colors.green[400] : Colors.orange[700],
        ),
        title: Text(
          enabled ? 'Auto-paste enabled' : 'Auto-paste disabled',
          style: const TextStyle(fontWeight: FontWeight.w600),
        ),
        subtitle: Text(
          enabled
              ? 'Murmur Accessibility Service is active'
              : 'Tap to enable the Accessibility Service for auto-paste',
        ),
        trailing: enabled
            ? null
            : TextButton(
                onPressed: onEnable,
                child: const Text('Enable'),
              ),
        onTap: enabled ? null : onEnable,
      ),
    );
  }
}

class _TipCard extends StatelessWidget {
  final IconData icon;
  final String text;

  const _TipCard({required this.icon, required this.text});

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(12),
      decoration: BoxDecoration(
        color: cs.surfaceContainerHighest.withOpacity(0.5),
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        children: [
          Icon(icon, size: 20, color: cs.primary),
          const SizedBox(width: 12),
          Expanded(
            child: Text(text,
                style: Theme.of(context)
                    .textTheme
                    .bodySmall
                    ?.copyWith(color: cs.onSurfaceVariant)),
          ),
        ],
      ),
    );
  }
}

// ── Setup card — shown when no server is configured ────────────────────────

class _SetupCard extends StatelessWidget {
  const _SetupCard();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: cs.primary.withOpacity(0.08),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: cs.primary.withOpacity(0.25)),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.computer, size: 18, color: cs.primary),
              const SizedBox(width: 8),
              Text(
                'Desktop app required',
                style: Theme.of(context).textTheme.titleSmall?.copyWith(
                      color: cs.primary,
                      fontWeight: FontWeight.w600,
                    ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Text(
            'Murmur transcribes your voice via a local Whisper server '
            'running on your PC or home server. Download and set up the '
            'desktop app first, then add the server URL in Settings.',
            style: Theme.of(context)
                .textTheme
                .bodySmall
                ?.copyWith(color: cs.onSurfaceVariant),
          ),
          const SizedBox(height: 12),
          GestureDetector(
            onTap: _openWebsite,
            child: Row(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  'Get started at murmurlabs.dev',
                  style: Theme.of(context).textTheme.bodySmall?.copyWith(
                        color: cs.primary,
                        fontWeight: FontWeight.w600,
                      ),
                ),
                const SizedBox(width: 4),
                Icon(Icons.open_in_new, size: 14, color: cs.primary),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

// ── Footer — always visible at the bottom ─────────────────────────────────

class _Footer extends StatelessWidget {
  const _Footer();

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    return Center(
      child: GestureDetector(
        onTap: _openWebsite,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 8),
          child: Row(
            mainAxisSize: MainAxisSize.min,
            children: [
              Text(
                'murmurlabs.dev',
                style: Theme.of(context).textTheme.bodySmall?.copyWith(
                      color: cs.onSurfaceVariant,
                    ),
              ),
              const SizedBox(width: 3),
              Icon(Icons.open_in_new, size: 11, color: cs.onSurfaceVariant),
            ],
          ),
        ),
      ),
    );
  }
}
