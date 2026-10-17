package net.spxcorp.jennys_rewards

import android.net.Uri
import android.webkit.CookieManager
import android.view.WindowManager
import io.flutter.embedding.android.FlutterActivity
import io.flutter.embedding.engine.FlutterEngine
import io.flutter.plugin.common.MethodChannel

class MainActivity : FlutterActivity() {
    private var savedBrightness: Float? = null
    private var previouslyKeptAwake = false
    override fun configureFlutterEngine(flutterEngine: FlutterEngine) {
        super.configureFlutterEngine(flutterEngine)
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "net.spxcorp.jennys/experience")
            .setMethodCallHandler { call, result ->
                val preferences = getSharedPreferences("jennys_experience", MODE_PRIVATE)
                when (call.method) {
                    "hasSeenIntroduction" -> result.success(preferences.getBoolean("introduction_seen_v1", false))
                    "completeIntroduction" -> {
                        if (preferences.edit().putBoolean("introduction_seen_v1", true).commit()) {
                            result.success(null)
                        } else {
                            result.error("PREFERENCE_UNAVAILABLE", "The introduction preference could not be saved.", null)
                        }
                    }
                    else -> result.notImplemented()
                }
            }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "net.spxcorp.jennys/card_display")
            .setMethodCallHandler { call, result ->
                when (call.method) {
                    "show" -> {
                        if (savedBrightness == null) {
                            savedBrightness = window.attributes.screenBrightness
                            previouslyKeptAwake = (window.attributes.flags and WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON) != 0
                        }
                        window.attributes = window.attributes.apply { screenBrightness = 1f }
                        window.addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                        result.success(null)
                    }
                    "hide" -> {
                        savedBrightness?.let { previous ->
                            window.attributes = window.attributes.apply { screenBrightness = previous }
                            if (!previouslyKeptAwake) window.clearFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON)
                            savedBrightness = null
                        }
                        result.success(null)
                    }
                    else -> result.notImplemented()
                }
            }
        MethodChannel(flutterEngine.dartExecutor.binaryMessenger, "net.spxcorp.jennys/session")
            .setMethodCallHandler { call, result ->
                val cookies = CookieManager.getInstance()
                when (call.method) {
                    "set" -> {
                        val origin = call.argument<String>("origin") ?: ""
                        val session = call.argument<String>("session") ?: ""
                        val uri = Uri.parse(origin)
                        if (uri.scheme != "https" || uri.host.isNullOrEmpty() ||
                            !uri.userInfo.isNullOrEmpty() || !uri.query.isNullOrEmpty() ||
                            !uri.fragment.isNullOrEmpty() ||
                            !(uri.path.isNullOrEmpty() || uri.path == "/") ||
                            !Regex("^[A-Za-z0-9_-]{20,256}$").matches(session)) {
                            result.error("INVALID_SESSION", "A valid secure website session is required.", null)
                        } else {
                            // Host-only cookie: no Domain attribute, no token in a URL or JavaScript.
                            cookies.setCookie(origin, "session_id=$session; Path=/; Secure; HttpOnly; SameSite=Lax") { accepted ->
                                cookies.flush()
                                if (accepted) result.success(null)
                                else result.error("COOKIE_REJECTED", "The website session could not be opened.", null)
                            }
                        }
                    }
                    "clear" -> cookies.removeAllCookies { cookies.flush(); result.success(null) }
                    else -> result.notImplemented()
                }
            }
    }
}
