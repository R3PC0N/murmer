import 'package:flutter/material.dart';
import 'package:uuid/uuid.dart';

import '../../models/profile.dart';
import '../../services/storage_service.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  final _storage = StorageService.instance;

  List<Profile> _profiles = [];
  String _activeId = 'default';

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    setState(() {
      _profiles = _storage.getProfiles();
      _activeId = _storage.getActiveProfileId();
    });
  }

  Future<void> _openEdit({Profile? profile}) async {
    await showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _ProfileEditor(existing: profile),
    );
    _load();
  }

  void _delete(Profile profile) {
    if (profile.id == 'default') return;
    showDialog(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Delete profile?'),
        content: Text('Remove "${profile.name}"?'),
        actions: [
          TextButton(
              onPressed: () => Navigator.pop(ctx), child: const Text('Cancel')),
          TextButton(
            onPressed: () {
              Navigator.pop(ctx);
              _storage.deleteProfile(profile.id);
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
      appBar: AppBar(
        title: const Text('Profiles'),
        actions: [
          IconButton(
            icon: const Icon(Icons.add),
            onPressed: () => _openEdit(),
            tooltip: 'New profile',
          ),
        ],
      ),
      body: ListView.builder(
        itemCount: _profiles.length,
        itemBuilder: (ctx, i) {
          final p = _profiles[i];
          final isActive = p.id == _activeId;
          return ListTile(
            leading: Radio<String>(
              value: p.id,
              groupValue: _activeId,
              onChanged: (val) {
                if (val != null) {
                  _storage.setActiveProfileId(val);
                  setState(() => _activeId = val);
                }
              },
            ),
            title: Text(p.name,
                style: isActive
                    ? const TextStyle(fontWeight: FontWeight.bold)
                    : null),
            subtitle: Text('${p.style.label}'
                '${p.userContext.isNotEmpty ? ' · has context' : ''}'),
            trailing: p.id == 'default'
                ? null
                : Row(
                    mainAxisSize: MainAxisSize.min,
                    children: [
                      IconButton(
                        icon: const Icon(Icons.edit_outlined, size: 20),
                        onPressed: () => _openEdit(profile: p),
                      ),
                      IconButton(
                        icon: const Icon(Icons.delete_outline, size: 20),
                        onPressed: () => _delete(p),
                      ),
                    ],
                  ),
            onTap: () => _openEdit(profile: p),
          );
        },
      ),
    );
  }
}

// ── Profile editor (bottom sheet) ─────────────────────────────────────────

class _ProfileEditor extends StatefulWidget {
  final Profile? existing;
  const _ProfileEditor({this.existing});

  @override
  State<_ProfileEditor> createState() => _ProfileEditorState();
}

class _ProfileEditorState extends State<_ProfileEditor> {
  final _storage = StorageService.instance;
  final _nameCtrl = TextEditingController();
  final _contextCtrl = TextEditingController();
  final _customCtrl = TextEditingController();
  final _correctionsCtrl = TextEditingController();

  TranscriptionStyle _style = TranscriptionStyle.none;

  @override
  void initState() {
    super.initState();
    final p = widget.existing;
    if (p != null) {
      _nameCtrl.text = p.name;
      _style = p.style;
      _contextCtrl.text = p.userContext;
      _customCtrl.text = p.customInstruction;
      _correctionsCtrl.text =
          p.wordCorrections.entries.map((e) => '${e.key}=${e.value}').join('\n');
    }
  }

  @override
  void dispose() {
    _nameCtrl.dispose();
    _contextCtrl.dispose();
    _customCtrl.dispose();
    _correctionsCtrl.dispose();
    super.dispose();
  }

  Map<String, String> _parseCorrections(String raw) {
    final result = <String, String>{};
    for (final line in raw.split('\n')) {
      final parts = line.split('=');
      if (parts.length == 2) {
        final key = parts[0].trim();
        final val = parts[1].trim();
        if (key.isNotEmpty && val.isNotEmpty) result[key] = val;
      }
    }
    return result;
  }

  void _save() {
    final name = _nameCtrl.text.trim();
    if (name.isEmpty) {
      ScaffoldMessenger.of(context)
          .showSnackBar(const SnackBar(content: Text('Name is required')));
      return;
    }

    final profile = Profile(
      id: widget.existing?.id ?? const Uuid().v4(),
      name: name,
      style: _style,
      customInstruction: _customCtrl.text.trim(),
      userContext: _contextCtrl.text.trim(),
      wordCorrections: _parseCorrections(_correctionsCtrl.text),
    );
    _storage.saveProfile(profile);
    // Auto-activate new profile
    if (widget.existing == null) {
      _storage.setActiveProfileId(profile.id);
    }
    Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final cs = Theme.of(context).colorScheme;
    final isNew = widget.existing == null;
    final isDefault = widget.existing?.id == 'default';

    return Padding(
      padding: EdgeInsets.only(
        bottom: MediaQuery.of(context).viewInsets.bottom,
      ),
      child: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisSize: MainAxisSize.min,
          children: [
            Row(
              children: [
                Text(isNew ? 'New profile' : 'Edit profile',
                    style: Theme.of(context).textTheme.titleLarge),
                const Spacer(),
                TextButton(onPressed: _save, child: const Text('Save')),
              ],
            ),
            const SizedBox(height: 16),

            TextField(
              controller: _nameCtrl,
              enabled: !isDefault,
              decoration: const InputDecoration(
                labelText: 'Profile name',
                prefixIcon: Icon(Icons.person_outline),
              ),
            ),
            const SizedBox(height: 20),

            Text('Transcription style',
                style: Theme.of(context).textTheme.labelMedium?.copyWith(
                      color: cs.onSurfaceVariant,
                    )),
            const SizedBox(height: 8),

            Wrap(
              spacing: 8,
              children: TranscriptionStyle.values.map((s) {
                return ChoiceChip(
                  label: Text(s.label),
                  selected: _style == s,
                  onSelected: (_) => setState(() => _style = s),
                );
              }).toList(),
            ),

            if (_style == TranscriptionStyle.custom) ...[
              const SizedBox(height: 12),
              TextField(
                controller: _customCtrl,
                maxLines: 3,
                decoration: const InputDecoration(
                  labelText: 'Custom style instruction',
                  hintText:
                      'e.g. Write in bullet points. Keep it short.',
                  alignLabelWithHint: true,
                ),
              ),
            ],
            const SizedBox(height: 16),

            TextField(
              controller: _contextCtrl,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'User context (optional)',
                hintText:
                    'e.g. I am a software developer. I often use technical terms.',
                alignLabelWithHint: true,
                prefixIcon: Padding(
                  padding: EdgeInsets.only(bottom: 48),
                  child: Icon(Icons.info_outline),
                ),
              ),
            ),
            const SizedBox(height: 16),

            TextField(
              controller: _correctionsCtrl,
              maxLines: 5,
              decoration: const InputDecoration(
                labelText: 'Word corrections (optional)',
                hintText: 'murmur=Murmur\ncuda=CUDA\nwhisper=Whisper',
                helperText: 'One correction per line: wrong=Correct',
                alignLabelWithHint: true,
                prefixIcon: Padding(
                  padding: EdgeInsets.only(bottom: 80),
                  child: Icon(Icons.spellcheck),
                ),
              ),
            ),
            const SizedBox(height: 24),
          ],
        ),
      ),
    );
  }
}
