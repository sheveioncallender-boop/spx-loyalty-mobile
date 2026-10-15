import Flutter
import UIKit
import WebKit

/// Mirrors the Android session-cookie contract without putting tokens in URLs or JavaScript.
enum SessionCookieFactory {
  static func make(origin: String, session: String) -> HTTPCookie? {
    guard let parts = URLComponents(string: origin),
      parts.scheme?.lowercased() == "https",
      let host = parts.host, !host.isEmpty,
      parts.user == nil, parts.password == nil,
      parts.query == nil, parts.fragment == nil,
      parts.path.isEmpty || parts.path == "/",
      session.range(of: "\\A[A-Za-z0-9_-]{20,256}\\z", options: .regularExpression) != nil,
      let url = parts.url
    else { return nil }

    // Omitting Domain makes the cookie host-only. A session cookie has no expiry.
    let header = "session_id=\(session); Path=/; Secure; HttpOnly; SameSite=Lax"
    let cookies = HTTPCookie.cookies(withResponseHeaderFields: ["Set-Cookie": header], for: url)
    return cookies.first { $0.name == "session_id" && $0.domain == host && $0.isSecure && $0.isHTTPOnly }
  }
}

final class NativeAppBridge {
  private let displayAid = CardDisplayAid()
  private var channels: [FlutterMethodChannel] = []

  func register(messenger: FlutterBinaryMessenger) {
    let session = FlutterMethodChannel(name: "net.spxcorp.jennys/session", binaryMessenger: messenger)
    session.setMethodCallHandler { call, result in
      let store = WKWebsiteDataStore.default()
      switch call.method {
      case "set":
        guard let args = call.arguments as? [String: Any],
          let origin = args["origin"] as? String,
          let token = args["session"] as? String,
          let cookie = SessionCookieFactory.make(origin: origin, session: token)
        else {
          result(FlutterError(code: "INVALID_SESSION", message: "A valid secure website session is required.", details: nil))
          return
        }
        // webview_flutter_wkwebview uses the same default WKWebsiteDataStore.
        store.httpCookieStore.setCookie(cookie) { result(nil) }
      case "clear":
        store.removeData(ofTypes: [WKWebsiteDataTypeCookies], modifiedSince: .distantPast) { result(nil) }
      default:
        result(FlutterMethodNotImplemented)
      }
    }

    let display = FlutterMethodChannel(name: "net.spxcorp.jennys/card_display", binaryMessenger: messenger)
    display.setMethodCallHandler { [weak self] call, result in
      guard let self = self else {
        result(FlutterError(code: "DISPLAY_UNAVAILABLE", message: "The display aid is unavailable.", details: nil))
        return
      }
      switch call.method {
      case "show": self.displayAid.setRequested(true); result(nil)
      case "hide": self.displayAid.setRequested(false); result(nil)
      default: result(FlutterMethodNotImplemented)
      }
    }
    channels = [session, display]
  }
}

/// Brightness and wake lock are temporary aids, restored when the app loses focus.
final class CardDisplayAid {
  private var requested = false
  private var previousBrightness: CGFloat?
  private var previousIdleTimer = false
  private var screen: UIScreen?
  private var observers: [NSObjectProtocol] = []

  init() {
    let center = NotificationCenter.default
    observers.append(center.addObserver(forName: UIApplication.willResignActiveNotification, object: nil, queue: .main) { [weak self] _ in
      self?.restore()
    })
    observers.append(center.addObserver(forName: UIApplication.didBecomeActiveNotification, object: nil, queue: .main) { [weak self] _ in
      self?.applyIfRequested()
    })
  }

  deinit {
    observers.forEach { NotificationCenter.default.removeObserver($0) }
    restore()
  }

  func setRequested(_ value: Bool) {
    requested = value
    if value { applyIfRequested() } else { restore() }
  }

  private func applyIfRequested() {
    guard requested, UIApplication.shared.applicationState == .active, previousBrightness == nil else { return }
    let activeScreen = UIApplication.shared.connectedScenes
      .compactMap { $0 as? UIWindowScene }
      .first { $0.activationState == .foregroundActive }?.screen ?? UIScreen.main
    screen = activeScreen
    previousBrightness = activeScreen.brightness
    previousIdleTimer = UIApplication.shared.isIdleTimerDisabled
    activeScreen.brightness = 1
    UIApplication.shared.isIdleTimerDisabled = true
  }

  private func restore() {
    guard let brightness = previousBrightness else { return }
    screen?.brightness = brightness
    UIApplication.shared.isIdleTimerDisabled = previousIdleTimer
    previousBrightness = nil
    screen = nil
  }
}
