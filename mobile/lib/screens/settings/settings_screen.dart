import 'package:flutter/material.dart';

import '../../models/server_config.dart';
import '../../services/storage_service.dart';
import 'server_settings_screen.dart';

class SettingsScreen extends StatefulWidget {
  const SettingsScreen({super.key});

  @override
  State<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends State<SettingsScreen> {
  final _storage = StorageService.instance;

  List<ServerConfig> _servers = [];
  String? _activeServerId;
  bool _aiEnabled = false;
  bool _autoStartOnBoot = false;
  final _anthropicController = TextEditingController();
  bool _showKey = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    setState(() {
      _servers = _storage.getServers();
      _activeServerId = _storage.getActiveServerId();
      _aiEnabled = _storage.isAiCleanupEnabled();
      _autoStartOnBoot = _storage.isAutoStartOnBoot();
      _anthropicController.text = _storage.getAnthropicKey();
    });
  }

  @override
  void dispose() {
    _anthropicController.dispose();
    super.dispose();
  }

  Future<void> _openAddServer({ServerConfig? existing}) async {
    await Navigator.push(
      context,
      MaterialPageRoute(
        builder: (_) => ServerSettingsScreen(existing: existing),
      ),
    );
    _load();
  }

  void _deleteServer(ServerConfig server) {
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete server?'),
        content: Text('Remove "${server.name}"?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              _storage.deleteServer(server.id);
              _load();
            },
            child: const Text('Delete', style: TextStyle(color: Colors.red)),
          ),
        ],
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Settings')),
      body: ListView(
        children: [
          // ── Servers ────────────────────────────────────────────────────
          _SectionHeader('Servers'),
          ..._servers.map((s) => ListTile(
                leading: Radio<String>(
                  value: s.id,
                  groupValue: _activeServerId,
                  onChanged: (val) {
                    _storage.setActiveServerId(val);
                    setState(() => _activeServerId = val);
                  },
                ),
                title: Text(s.name),
                subtitle: Text(s.displayUrl),
                trailing: Row(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    IconButton(
                      icon: const Icon(Icons.edit_outlined, size: 20),
                      onPressed: () => _openAddServer(existing: s),
                    ),
                    IconButton(
                      icon: const Icon(Icons.delete_outline, size: 20),
                      onPressed: () => _deleteServer(s),
                    ),
                  ],
                ),
              )),
          ListTile(
            leading: const Icon(Icons.add_circle_outline),
            title: const Text('Add server'),
            onTap: () => _openAddServer(),
          ),
          const Divider(),

          // ── AI Cleanup ─────────────────────────────────────────────────
          _SectionHeader('AI Cleanup'),
          SwitchListTile(
            title: const Text('Enable Claude Haiku cleanup'),
            subtitle: const Text(
                'Fixes filler words, punctuation and style after transcription'),
            value: _aiEnabled,
            onChanged: (val) {
              _storage.setAiCleanupEnabled(val);
              setState(() => _aiEnabled = val);
            },
          ),
          if (_aiEnabled)
            Padding(
              padding:
                  const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
              child: TextField(
                controller: _anthropicController,
                obscureText: !_showKey,
                decoration: InputDecoration(
                  labelText: 'Anthropic API key',
                  hintText: 'sk-ant-...',
                  suffixIcon: IconButton(
                    icon:
                        Icon(_showKey ? Icons.visibility_off : Icons.visibility),
                    onPressed: () => setState(() => _showKey = !_showKey),
                  ),
                ),
                onChanged: _storage.setAnthropicKey,
              ),
            ),
          const Divider(),

          // ── Overlay ────────────────────────────────────────────────────
          _SectionHeader('Overlay'),
          SwitchListTile(
            secondary: const Icon(Icons.start_outlined),
            title: const Text('Auto-start on boot'),
            subtitle: const Text(
                'Show the floating mic button automatically when the device starts'),
            value: _autoStartOnBoot,
            onChanged: (val) {
              _storage.setAutoStartOnBoot(val);
              setState(() => _autoStartOnBoot = val);
            },
          ),
          const Divider(),

          // ── About ──────────────────────────────────────────────────────
          _SectionHeader('About'),
          ListTile(
            leading: const Icon(Icons.info_outline),
            title: const Text('Murmer Mobile'),
            subtitle: const Text('Voice dictation via remote Whisper server'),
          ),
          ListTile(
            leading: const Icon(Icons.code),
            title: const Text('github.com/R3PC0N/murmer'),
          ),
          const SizedBox(height: 24),
        ],
      ),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 20, 16, 4),
      child: Text(
        title.toUpperCase(),
        style: Theme.of(context).textTheme.labelSmall?.copyWith(
              color: Theme.of(context).colorScheme.primary,
              letterSpacing: 1.2,
            ),
      ),
    );
  }
}
