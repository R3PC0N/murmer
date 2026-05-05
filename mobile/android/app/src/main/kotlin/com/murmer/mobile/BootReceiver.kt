package com.murmer.mobile

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.util.Log

class BootReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return

        Log.d("BootReceiver", "Boot completed received")

        // Read SharedPreferences written by Flutter's shared_preferences plugin.
        // Keys are prefixed with "flutter." by the plugin.
        val prefs = context.getSharedPreferences(
            "FlutterSharedPreferences",
            Context.MODE_PRIVATE
        )
        val autoStart = prefs.getBoolean("flutter.auto_start_on_boot", false)
        Log.d("BootReceiver", "auto_start_on_boot = $autoStart")

        if (!autoStart) return

        // Launch MainActivity with a flag to auto-start the overlay.
        // The activity will start the overlay then move itself to the background.
        val launchIntent = Intent(context, MainActivity::class.java).apply {
            addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_NO_ANIMATION)
            putExtra("auto_start_overlay", true)
        }
        context.startActivity(launchIntent)
    }
}
