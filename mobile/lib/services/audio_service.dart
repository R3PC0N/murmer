import 'dart:io';
import 'package:path_provider/path_provider.dart';
import 'package:record/record.dart';

class AudioService {
  final AudioRecorder _recorder = AudioRecorder();

  Future<bool> hasPermission() => _recorder.hasPermission();

  Future<void> startRecording() async {
    final dir = await getTemporaryDirectory();
    final path = '${dir.path}/murmur_recording.wav';

    await _recorder.start(
      const RecordConfig(
        encoder: AudioEncoder.wav,
        sampleRate: 16000,
        numChannels: 1,
        bitRate: 256000,
      ),
      path: path,
    );
  }

  Future<File?> stopRecording() async {
    final path = await _recorder.stop();
    if (path == null) return null;
    final file = File(path);
    return file.existsSync() ? file : null;
  }

  Future<bool> get isRecording => _recorder.isRecording();

  void dispose() => _recorder.dispose();
}
