import Flutter
import UIKit
import XCTest
@testable import Runner

class RunnerTests: XCTestCase {

  private let token = String(repeating: "a", count: 40)

  func testSessionCookieIsSecureHTTPOnlyAndHostScoped() throws {
    let cookie = try XCTUnwrap(SessionCookieFactory.make(origin: "https://jennys.example", session: token))
    XCTAssertEqual(cookie.name, "session_id")
    XCTAssertEqual(cookie.value, token)
    XCTAssertEqual(cookie.domain, "jennys.example")
    XCTAssertEqual(cookie.path, "/")
    XCTAssertTrue(cookie.isSecure)
    XCTAssertTrue(cookie.isHTTPOnly)
    XCTAssertNil(cookie.expiresDate)
  }

  func testRejectsInsecureOrAmbiguousOrigins() {
    for origin in ["http://jennys.example", "https://user:pass@jennys.example", "https://jennys.example/account", "https://jennys.example?session=x", "https://jennys.example#x", "jennys://account/verified"] {
      XCTAssertNil(SessionCookieFactory.make(origin: origin, session: token), origin)
    }
  }

  func testRejectsEmptyShortOverlongAndHeaderInjectionTokens() {
    for value in ["", "short", String(repeating: "a", count: 257), token + "; Domain=example", token + "\r\nX-Test: value", token + "\n"] {
      XCTAssertNil(SessionCookieFactory.make(origin: "https://jennys.example", session: value))
    }
  }

}
