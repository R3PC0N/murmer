package com.murmer.mobile

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.AccessibilityServiceInfo
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo

class MurmerAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "MurmerA11y"

        @Volatile var instance: MurmerAccessibilityService? = null

        @JvmStatic
        fun pasteText(text: String): Boolean {
            val service = instance ?: run {
                Log.w(TAG, "service not connected")
                return false
            }
            return service.doPaste(text)
        }

        @JvmStatic
        fun isConnected(): Boolean = instance != null
    }

    private val mainHandler = Handler(Looper.getMainLooper())
    private val hideRunnable = Runnable { setOverlayVisible(false) }

    @Volatile private var lastEditableWindowId: Int = -1

    override fun onServiceConnected() {
        Log.d(TAG, "onServiceConnected")
        instance = this

        // Required to receive TYPE_WINDOWS_CHANGED and to use getWindows()
        val info = serviceInfo
        info.flags = info.flags or AccessibilityServiceInfo.FLAG_RETRIEVE_INTERACTIVE_WINDOWS
        serviceInfo = info

        // Start hidden
        setOverlayVisible(false)
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return

        when (event.eventType) {

            // Keyboard appeared or disappeared — most reliable signal
            AccessibilityEvent.TYPE_WINDOWS_CHANGED -> {
                val keyboardVisible = try {
                    windows?.any { it.type == AccessibilityWindowInfo.TYPE_INPUT_METHOD } == true
                } catch (e: Exception) { false }

                Log.d(TAG, "windows changed — keyboard=$keyboardVisible")

                mainHandler.removeCallbacks(hideRunnable)
                if (keyboardVisible) {
                    setOverlayVisible(true)
                } else {
                    // Small delay so overlay doesn't flicker when switching fields
                    mainHandler.postDelayed(hideRunnable, 400)
                }
            }

            // Track which window had an editable field (needed for paste)
            AccessibilityEvent.TYPE_VIEW_FOCUSED -> {
                val source = event.source ?: return
                if (source.isEditable) {
                    lastEditableWindowId = event.windowId
                    Log.d(TAG, "tracked editable: windowId=$lastEditableWindowId")
                }
                source.recycle()
            }
        }
    }

    // ── Overlay visibility ────────────────────────────────────────────────────

    private fun setOverlayVisible(visible: Boolean) {
        try {
            val cls = Class.forName(
                "flutter.overlay.window.flutter_overlay_window.OverlayService"
            )
            val svc = cls.getField("instance").get(null) ?: return
            cls.getMethod("setOverlayVisible", Boolean::class.javaPrimitiveType)
                .invoke(svc, visible)
            Log.d(TAG, "overlay visible=$visible")
        } catch (e: Exception) {
            Log.w(TAG, "setOverlayVisible failed: $e")
        }
    }

    // ── Paste ─────────────────────────────────────────────────────────────────

    private fun doPaste(text: String): Boolean {
        Log.d(TAG, "doPaste — '${text.take(30)}'")

        // Strategy 1: use the input-focused node (works in most standard apps)
        val focused = findFocusedNode()
        if (focused != null) {
            Log.d(TAG, "node: ${focused.className} editable=${focused.isEditable}")

            val pasteOk = focused.performAction(AccessibilityNodeInfo.ACTION_PASTE)
            Log.d(TAG, "ACTION_PASTE on focused: $pasteOk")
            if (pasteOk) { focused.recycle(); return true }

            val args = Bundle()
            args.putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text
            )
            val setOk = focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
            Log.d(TAG, "ACTION_SET_TEXT on focused: $setOk")
            focused.recycle()
            if (setOk) return true
        } else {
            Log.w(TAG, "no focused node — falling through to tree search")
        }

        // Strategy 2: walk the active window tree and paste into the first editable node.
        // Handles apps (e.g. Samsung Notes) whose custom editor doesn't report input focus
        // via standard accessibility focus queries.
        val root = rootInActiveWindow
        if (root != null) {
            Log.d(TAG, "trying tree-walk paste in active window")
            val ok = pasteIntoFirstEditable(root, text)
            root.recycle()
            if (ok) return true
        }

        Log.w(TAG, "all paste strategies exhausted")
        return false
    }

    /**
     * Depth-first search for the first editable node and attempt paste / set-text.
     * Returns true as soon as one strategy succeeds.
     */
    private fun pasteIntoFirstEditable(node: AccessibilityNodeInfo, text: String): Boolean {
        if (node.isEditable) {
            val pasteOk = node.performAction(AccessibilityNodeInfo.ACTION_PASTE)
            Log.d(TAG, "tree-walk ACTION_PASTE on ${node.className}: $pasteOk")
            if (pasteOk) return true

            val args = Bundle()
            args.putCharSequence(
                AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE, text
            )
            val setOk = node.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
            Log.d(TAG, "tree-walk ACTION_SET_TEXT on ${node.className}: $setOk")
            if (setOk) return true
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i) ?: continue
            val found = pasteIntoFirstEditable(child, text)
            child.recycle()
            if (found) return true
        }
        return false
    }

    private fun findFocusedNode(): AccessibilityNodeInfo? {
        val allWindows = try { windows } catch (e: Exception) { null }

        if (!allWindows.isNullOrEmpty()) {
            if (lastEditableWindowId >= 0) {
                allWindows.find { it.id == lastEditableWindowId }?.let { w ->
                    val root = w.root
                    val node = root?.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                    root?.recycle()
                    if (node != null) return node
                }
            }
            for (w in allWindows) {
                if (w.type == AccessibilityWindowInfo.TYPE_SYSTEM) continue
                val root = w.root ?: continue
                val node = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                root.recycle()
                if (node != null) return node
            }
        }

        val root = rootInActiveWindow ?: return null
        val node = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        root.recycle()
        return node
    }

    override fun onInterrupt() {}

    override fun onDestroy() {
        Log.d(TAG, "onDestroy")
        mainHandler.removeCallbacks(hideRunnable)
        instance = null
        super.onDestroy()
    }
}
