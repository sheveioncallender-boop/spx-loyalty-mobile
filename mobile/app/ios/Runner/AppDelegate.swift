import Flutter
import UIKit

@main
@objc class AppDelegate: FlutterAppDelegate, FlutterImplicitEngineDelegate {
  private let nativeBridge = NativeAppBridge()
  override func application(
    _ application: UIApplication,
    didFinishLaunchingWithOptions launchOptions: [UIApplication.LaunchOptionsKey: Any]?
  ) -> Bool {
    return super.application(application, didFinishLaunchingWithOptions: launchOptions)
  }

  func didInitializeImplicitFlutterEngine(_ engineBridge: FlutterImplicitEngineBridge) {
    GeneratedPluginRegistrant.register(with: engineBridge.pluginRegistry)
    nativeBridge.register(messenger: engineBridge.applicationRegistrar.messenger())
    let experience = FlutterMethodChannel(
      name: "net.spxcorp.jennys/experience",
      binaryMessenger: engineBridge.applicationRegistrar.messenger()
    )
    experience.setMethodCallHandler { call, result in
      switch call.method {
      case "hasSeenIntroduction":
        result(UserDefaults.standard.bool(forKey: "introduction_seen_v1"))
      case "completeIntroduction":
        UserDefaults.standard.set(true, forKey: "introduction_seen_v1")
        result(nil)
      default:
        result(FlutterMethodNotImplemented)
      }
    }
  }
}
