import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_theme.dart';
import 'overlay/mic_button_overlay.dart';
import 'screens/splash_screen.dart';
import 'services/storage_service.dart';

@pragma('vm:entry-point')
void overlayMain() {
  WidgetsFlutterBinding.ensureInitialized();
  // Use bare Directionality — no MaterialApp/Scaffold so no hidden background
  runApp(const Directionality(
    textDirection: TextDirection.ltr,
    child: MicButtonOverlay(),
  ));
}

void main() async {
  WidgetsFlutterBinding.ensureInitialized();

  // Portrait-only for now
  await SystemChrome.setPreferredOrientations([
    DeviceOrientation.portraitUp,
    DeviceOrientation.portraitDown,
  ]);

  await StorageService.instance.init();

  runApp(const MurmurApp());
}

class MurmurApp extends StatelessWidget {
  const MurmurApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Murmur',
      theme: AppTheme.light,
      darkTheme: AppTheme.dark,
      themeMode: ThemeMode.system,
      debugShowCheckedModeBanner: false,
      home: const SplashScreen(),
    );
  }
}
