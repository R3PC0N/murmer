import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;

import '../models/server_config.dart';
import '../models/profile.dart';

class TranscriptionResult {
  final String text;
  final String language;

  const TranscriptionResult({required this.text, required this.language});
}

class WhisperService {
  Future<void> checkHealth(ServerConfig server) async {
    final uri = Uri.parse('${_base(server)}/health');
    final resp = await http
        .get(uri, headers: _headers(server))
        .timeout(const Duration(seconds: 10));
    if (resp.statusCode != 200) {
      throw Exception('Server returned ${resp.statusCode}');
    }
  }

  Future<TranscriptionResult> transcribe(
    ServerConfig server,
    File audioFile, {
    Profile? profile,
    String? anthropicKey,
    bool aiCleanup = false,
  }) async {
    // Step 1: transcribe audio via Whisper server
    final uri = Uri.parse('${_base(server)}/transcribe');
    debugPrint('[Murmur] transcribe: building request to $uri');
    debugPrint('[Murmur] audio file: ${audioFile.path} exists=${audioFile.existsSync()} size=${audioFile.lengthSync()}');

    final request = http.MultipartRequest('POST', uri)
      ..headers.addAll(_headers(server))
      ..files.add(await http.MultipartFile.fromPath(
        'audio',
        audioFile.path,
        filename: 'audio.wav',
      ));

    debugPrint('[Murmur] sending request...');
    final resp = await Future(() async {
      final streamed = await request.send();
      debugPrint('[Murmur] response status: ${streamed.statusCode}');
      return http.Response.fromStream(streamed);
    }).timeout(const Duration(seconds: 30), onTimeout: () {
      debugPrint('[Murmur] TIMEOUT after 30s');
      throw TimeoutException('Transcription timed out after 30s');
    });
    debugPrint('[Murmur] response body length: ${resp.body.length}');

    if (resp.statusCode != 200) {
      throw Exception('Transcription failed (${resp.statusCode}): ${resp.body}');
    }

    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    String text = (data['text'] as String).trim();
    final language = data['language'] as String? ?? 'unknown';

    // Apply word corrections from active profile
    if (profile != null && profile.wordCorrections.isNotEmpty) {
      text = _applyCorrections(text, profile.wordCorrections);
    }

    // Step 2: optional AI cleanup via Anthropic
    if (aiCleanup && anthropicKey != null && anthropicKey.isNotEmpty && profile != null) {
      text = await _cleanWithClaude(text, profile, anthropicKey);
    }

    return TranscriptionResult(text: text, language: language);
  }

  String _applyCorrections(String text, Map<String, String> corrections) {
    var result = text;
    for (final entry in corrections.entries) {
      final pattern = RegExp(r'\b' + RegExp.escape(entry.key) + r'\b',
          caseSensitive: false);
      result = result.replaceAll(pattern, entry.value);
    }
    return result;
  }

  Future<String> _cleanWithClaude(
      String text, Profile profile, String apiKey) async {
    final stylePrompt = profile.effectiveStylePrompt;
    final contextBlock = profile.userContext.isNotEmpty
        ? '\nUser context: ${profile.userContext}'
        : '';

    final systemPrompt =
        'You are a transcription cleanup assistant. Fix filler words, improve punctuation and capitalization. '
        'Preserve the speaker\'s language (do not translate). Return ONLY the cleaned text, no commentary.'
        '${stylePrompt.isNotEmpty ? '\nStyle: $stylePrompt' : ''}'
        '$contextBlock';

    final body = jsonEncode({
      'model': 'claude-haiku-4-5-20251001',
      'max_tokens': 1024,
      'system': systemPrompt,
      'messages': [
        {'role': 'user', 'content': text}
      ],
    });

    final resp = await http
        .post(
          Uri.parse('https://api.anthropic.com/v1/messages'),
          headers: {
            'x-api-key': apiKey,
            'anthropic-version': '2023-06-01',
            'content-type': 'application/json',
          },
          body: body,
        )
        .timeout(const Duration(seconds: 20));

    if (resp.statusCode != 200) return text;

    final data = jsonDecode(resp.body) as Map<String, dynamic>;
    final content = (data['content'] as List?)?.first as Map?;
    return (content?['text'] as String?)?.trim() ?? text;
  }

  String _base(ServerConfig server) => server.url.replaceAll(RegExp(r'/+$'), '');
  Map<String, String> _headers(ServerConfig server) => {'X-API-Key': server.apiKey};
}
