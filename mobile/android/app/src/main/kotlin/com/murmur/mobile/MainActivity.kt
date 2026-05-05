package com.murmur.mobile

import android.content.Intent
import android.net.Uri
import android.provider.Settings
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {

    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)

        // Accessibility service status + settings
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.murmur/accessibility")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "isEnabled" -> result.success(MurmurAccessibilityService.isConnected())
                    "openSettings" -> {
                        startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS))
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }

        // Main app channel — used to pass boot intent flag to Flutter
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "com.murmur/main")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "shouldAutoStartOverlay" -> {
                        val flag = intent?.getBooleanExtra("auto_start_overlay", false) == true
                        // Clear the flag so it only fires once per launch
                        intent?.removeExtra("auto_start_overlay")
                        result.success(flag)
                    }
                    "moveToBackground" -> {
                        moveTaskToBack(true)
                        result.success(null)
                    }
                    "openUrl" -> {
                        val url = call.argument<String>("url") ?: ""
                        startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
    }
}
