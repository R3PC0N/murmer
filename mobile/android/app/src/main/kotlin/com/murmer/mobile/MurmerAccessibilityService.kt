package com.murmer.mobile

import android.accessibilityservice.AccessibilityService
import android.os.Bundle
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import android.view.accessibility.AccessibilityWindowInfo

class MurmerAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "MurmerA11y"

        @Volatile var instance: MurmerAccessibilityService? = null

        /**
         * Called via reflection from OverlayService.
         * Text is passed directly — Android 12+ blocks clipboard reads
         * from background services, so we can't read it here.
         * ACTION_PASTE still works (system injects clipboard), and
         * ACTION_SET_TEXT uses the provided text as fallback.
         */
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

    /** Window ID of the last window that contained an input-focused editable node. */
    @Volatile private var lastEditableWindowId: Int = -1

    override fun onServiceConnected() {
        Log.d(TAG, "onServiceConnected")
        instance = this
    }

    /** Track which window last had an editable input focus. */
    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event == null) return
        if (event.eventType == AccessibilityEvent.TYPE_VIEW_FOCUSED) {
            val source = event.source ?: return
            if (source.isEditable) {
                lastEditableWindowId = event.windowId
                Log.d(TAG, "tracked editable focus: windowId=$lastEditableWindowId pkg=${source.packageName}")
            }
            source.recycle()
        }
    }

    private fun doPaste(text: String): Boolean {
        Log.d(TAG, "doPaste — text='${text.take(30)}' lastEditableWindowId=$lastEditableWindowId")

        val focused = findFocusedNode()
        if (focused == null) {
            Log.w(TAG, "no focused node found")
            return false
        }

        Log.d(TAG, "node: class=${focused.className} editable=${focused.isEditable} pkg=${focused.packageName}")

        // Try ACTION_PASTE first — system injects clipboard content at cursor
        val pasteOk = focused.performAction(AccessibilityNodeInfo.ACTION_PASTE)
        Log.d(TAG, "ACTION_PASTE: $pasteOk")

        if (pasteOk) {
            focused.recycle()
            return true
        }

        // Fallback: ACTION_SET_TEXT with the text passed directly
        val args = Bundle()
        args.putCharSequence(
            AccessibilityNodeInfo.ACTION_ARGUMENT_SET_TEXT_CHARSEQUENCE,
            text
        )
        val setOk = focused.performAction(AccessibilityNodeInfo.ACTION_SET_TEXT, args)
        Log.d(TAG, "ACTION_SET_TEXT: $setOk")
        focused.recycle()
        return setOk
    }

    private fun findFocusedNode(): AccessibilityNodeInfo? {
        // 1. Try all windows
        val allWindows: List<AccessibilityWindowInfo>? = try {
            windows
        } catch (e: Exception) {
            Log.w(TAG, "getWindows() threw: $e")
            null
        }
        Log.d(TAG, "windows: ${allWindows?.size ?: "null"}")

        if (!allWindows.isNullOrEmpty()) {
            // Prefer the tracked window
            if (lastEditableWindowId >= 0) {
                allWindows.find { it.id == lastEditableWindowId }?.let { window ->
                    val root = window.root
                    val node = root?.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                    root?.recycle()
                    if (node != null) {
                        Log.d(TAG, "found in tracked window $lastEditableWindowId")
                        return node
                    }
                }
            }
            // Scan all non-system windows
            for (window in allWindows) {
                if (window.type == AccessibilityWindowInfo.TYPE_SYSTEM) continue
                val root = window.root ?: continue
                val node = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
                root.recycle()
                if (node != null) {
                    Log.d(TAG, "found in window id=${window.id} type=${window.type}")
                    return node
                }
            }
        }

        // 2. Fallback: rootInActiveWindow
        val root = rootInActiveWindow
        Log.d(TAG, "rootInActiveWindow pkg=${root?.packageName}")
        if (root == null) return null
        val node = root.findFocus(AccessibilityNodeInfo.FOCUS_INPUT)
        Log.d(TAG, "rootInActiveWindow node: class=${node?.className} editable=${node?.isEditable}")
        root.recycle()
        return node
    }

    override fun onInterrupt() {}

    override fun onDestroy() {
        Log.d(TAG, "onDestroy")
        instance = null
        super.onDestroy()
    }
}
