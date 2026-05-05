import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import 'app_theme.dart';
import 'overlay/mic_button_overlay.dart';
import 'screens/home_screen.dart';
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

  runApp(const MurmerApp());
}

class MurmerApp extends StatelessWidget {
  const MurmerApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Murmer',
      theme: AppTheme.dark,
      debugShowCheckedModeBanner: false,
      home: const HomeScreen(),
    );
  }
}
