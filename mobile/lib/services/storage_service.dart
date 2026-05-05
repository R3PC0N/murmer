import 'dart:convert';
import 'package:shared_preferences/shared_preferences.dart';

import '../models/server_config.dart';
import '../models/profile.dart';

class StorageService {
  static final StorageService _instance = StorageService._();
  static StorageService get instance => _instance;
  StorageService._();

  late SharedPreferences _prefs;

  static const _keyServers = 'servers';
  static const _keyActiveServerId = 'active_server_id';
  static const _keyProfiles = 'profiles';
  static const _keyActiveProfileId = 'active_profile_id';
  static const _keyAnthropicKey = 'anthropic_api_key';
  static const _keyAiCleanup = 'ai_cleanup_enabled';
  static const _keyAutoStartOnBoot = 'auto_start_on_boot';

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
    await _prefs.reload(); // Always sync from disk — overlay engine may have stale cache
    _ensureDefaults();
  }

  void _ensureDefaults() {
    if (getProfiles().isEmpty) {
      saveProfile(Profile.defaultProfile);
    }
  }

  // ── Servers ──────────────────────────────────────────────────────────────

  List<ServerConfig> getServers() {
    final raw = _prefs.getStringList(_keyServers) ?? [];
    return raw
        .map((s) => ServerConfig.fromJson(jsonDecode(s) as Map<String, dynamic>))
        .toList();
  }

  void saveServer(ServerConfig server) {
    final servers = getServers();
    final idx = servers.indexWhere((s) => s.id == server.id);
    if (idx >= 0) {
      servers[idx] = server;
    } else {
      servers.add(server);
    }
    _persistServers(servers);
  }

  void deleteServer(String id) {
    final servers = getServers().where((s) => s.id != id).toList();
    _persistServers(servers);
    if (getActiveServerId() == id) setActiveServerId(null);
  }

  void _persistServers(List<ServerConfig> servers) {
    _prefs.setStringList(
      _keyServers,
      servers.map((s) => jsonEncode(s.toJson())).toList(),
    );
  }

  String? getActiveServerId() => _prefs.getString(_keyActiveServerId);

  void setActiveServerId(String? id) {
    if (id == null) {
      _prefs.remove(_keyActiveServerId);
    } else {
      _prefs.setString(_keyActiveServerId, id);
    }
  }

  ServerConfig? getActiveServer() {
    final id = getActiveServerId();
    if (id == null) return null;
    try {
      return getServers().firstWhere((s) => s.id == id);
    } catch (_) {
      return null;
    }
  }

  // ── Profiles ─────────────────────────────────────────────────────────────

  List<Profile> getProfiles() {
    final raw = _prefs.getStringList(_keyProfiles) ?? [];
    return raw
        .map((s) => Profile.fromJson(jsonDecode(s) as Map<String, dynamic>))
        .toList();
  }

  void saveProfile(Profile profile) {
    final profiles = getProfiles();
    final idx = profiles.indexWhere((p) => p.id == profile.id);
    if (idx >= 0) {
      profiles[idx] = profile;
    } else {
      profiles.add(profile);
    }
    _persistProfiles(profiles);
  }

  void deleteProfile(String id) {
    if (id == 'default') return;
    final profiles = getProfiles().where((p) => p.id != id).toList();
    _persistProfiles(profiles);
    if (getActiveProfileId() == id) setActiveProfileId('default');
  }

  void _persistProfiles(List<Profile> profiles) {
    _prefs.setStringList(
      _keyProfiles,
      profiles.map((p) => jsonEncode(p.toJson())).toList(),
    );
  }

  String getActiveProfileId() =>
      _prefs.getString(_keyActiveProfileId) ?? 'default';

  void setActiveProfileId(String id) =>
      _prefs.setString(_keyActiveProfileId, id);

  Profile getActiveProfile() {
    final id = getActiveProfileId();
    try {
      return getProfiles().firstWhere((p) => p.id == id);
    } catch (_) {
      return Profile.defaultProfile;
    }
  }

  // ── AI Cleanup ────────────────────────────────────────────────────────────

  String getAnthropicKey() => _prefs.getString(_keyAnthropicKey) ?? '';
  void setAnthropicKey(String key) => _prefs.setString(_keyAnthropicKey, key);

  bool isAiCleanupEnabled() => _prefs.getBool(_keyAiCleanup) ?? false;
  void setAiCleanupEnabled(bool val) => _prefs.setBool(_keyAiCleanup, val);

  // ── Auto-start on boot ────────────────────────────────────────────────────

  bool isAutoStartOnBoot() => _prefs.getBool(_keyAutoStartOnBoot) ?? false;
  void setAutoStartOnBoot(bool val) => _prefs.setBool(_keyAutoStartOnBoot, val);
}
