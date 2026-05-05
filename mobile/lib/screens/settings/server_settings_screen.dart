import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../../models/server_config.dart';
import '../../services/storage_service.dart';
import '../../services/whisper_service.dart';

class ServerSettingsScreen extends StatefulWidget {
  final ServerConfig? existing;

  const ServerSettingsScreen({super.key, this.existing});

  @override
  State<ServerSettingsScreen> createState() => _ServerSettingsScreenState();
}

class _ServerSettingsScreenState extends State<ServerSettingsScreen> {
  final _formKey = GlobalKey<FormState>();
  final _storage = StorageService.instance;
  final _whisper = WhisperService();

  late final TextEditingController _nameCtrl;
  late final TextEditingController _urlCtrl;
  late final TextEditingController _keyCtrl;

  bool _showKey = false;
  bool _testing = false;
  String? _testResult;
  bool _testOk = false;

  @override
  void initState() {
    super.initState();
    _nameCtrl = TextEditingController(text: widget.existing?.name ?? '');
    _urlCtrl = TextEditingController(
        text: widget.existing?.url ?? 'http://');
    _keyCtrl = TextEditingController(text: widget.existing?.apiKey ?? '');
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _urlCtrl.dispose();
    _keyCtrl.dispose();
    super.dispose();
  }

  Future<void> _testConnection() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() {
      _testing = true;
      _testResult = null;
    });

    final server = ServerConfig(
      id: widget.existing?.id ?? const Uuid().v4(),
      name: _nameCtrl.text.trim(),
      url: _urlCtrl.text.trim(),
      apiKey: _keyCtrl.text.trim(),
    );

    try {
      await _whisper.checkHealth(server);
      setState(() {
        _testing = false;
        _testOk = true;
        _testResult = 'Connected successfully';
      });
    } catch (e) {
      setState(() {
        _testing = false;
        _testOk = false;
        _testResult = 'Failed: $e';
      });
    }
  }

  void _save() {
    if (!_formKey.currentState!.validate()) return;
    final server = ServerConfig(
      id: widget.existing?.id ?? const Uuid().v4(),
      name: _nameCtrl.text.trim(),
      url: _urlCtrl.text.trim(),
      apiKey: _keyCtrl.text.trim(),
    );
    _storage.saveServer(server);
    // Auto-select if it's the first server
    if (_storage.getActiveServerId() == null) {
      _storage.setActiveServerId(server.id);
    }
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final isNew = widget.existing == null;

    return Scaffold(
      appBar: AppBar(
        title: Text(isNew ? 'Add server' : 'Edit server'),
        actions: [
          TextButton(
            onPressed: _save,
            child: const Text('Save'),
          ),
        ],
      ),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            TextFormField(
              controller: _nameCtrl,
              decoration: const InputDecoration(
                labelText: 'Name',
                hintText: 'e.g. Home desktop',
                prefixIcon: Icon(Icons.label_outline),
              ),
              validator: (v) =>
                  (v == null || v.trim().isEmpty) ? 'Name is required' : null,
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 16),

            TextFormField(
              controller: _urlCtrl,
              decoration: const InputDecoration(
                labelText: 'Server URL',
                hintText: 'http://192.168.1.x:8765',
                prefixIcon: Icon(Icons.link),
              ),
              keyboardType: TextInputType.url,
              autocorrect: false,
              validator: (v) {
                if (v == null || v.trim().isEmpty) return 'URL is required';
                final uri = Uri.tryParse(v.trim());
                if (uri == null || !uri.hasScheme) return 'Enter a valid URL';
                return null;
              },
              textInputAction: TextInputAction.next,
            ),
            const SizedBox(height: 16),

            TextFormField(
              controller: _keyCtrl,
              obscureText: !_showKey,
              decoration: InputDecoration(
                labelText: 'API key',
                hintText: 'Your MURMER_API_KEY from the server .env',
                prefixIcon: const Icon(Icons.key_outlined),
                suffixIcon: IconButton(
                  icon: Icon(_showKey ? Icons.visibility_off : Icons.visibility),
                  onPressed: () => setState(() => _showKey = !_showKey),
                ),
              ),
              autocorrect: false,
              enableSuggestions: false,
            ),
            const SizedBox(height: 24),

            // Connection test
            OutlinedButton.icon(
              onPressed: _testing ? null : _testConnection,
              icon: _testing
                  ? const SizedBox(
                      width: 16,
                      height: 16,
                      child: CircularProgressIndicator(strokeWidth: 2),
                    )
                  : const Icon(Icons.wifi_tethering),
              label: Text(_testing ? 'Testing…' : 'Test connection'),
            ),

            if (_testResult != null) ...[
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(12),
                decoration: BoxDecoration(
                  color: (_testOk ? Colors.green : Colors.red)
                      .withOpacity(0.15),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Row(
                  children: [
                    Icon(
                      _testOk ? Icons.check_circle : Icons.error_outline,
                      color: _testOk ? Colors.green : Colors.red,
                      size: 18,
                    ),
                    const SizedBox(width: 8),
                    Expanded(child: Text(_testResult!)),
                  ],
                ),
              ),
            ],

            const SizedBox(height: 32),

            // Help text
            Text(
              'The URL can be a local IP (http://192.168.x.x:8765), '
              'a Tailscale IP (http://100.x.x.x:8765), or a domain with '
              'a reverse proxy (https://whisper.yourdomain.com).',
              style: Theme.of(context).textTheme.bodySmall?.copyWith(
                    color: Theme.of(context).colorScheme.onSurfaceVariant,
                  ),
            ),
          ],
        ),
      ),
    );
  }
}
