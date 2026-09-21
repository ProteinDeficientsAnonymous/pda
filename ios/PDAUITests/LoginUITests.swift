import XCTest

final class LoginUITests: XCTestCase {
    func test_signInIsPhoneThenPassword_lowercase_noJoin() {
        let app = XCUIApplication()
        app.launchArguments = ["--reset-session"]
        app.launch()

        XCTAssertTrue(app.buttons["sign in"].waitForExistence(timeout: 20))
        app.buttons["sign in"].tap()

        XCTAssertTrue(app.staticTexts["welcome back"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["sign in to your pda account"].exists)
        XCTAssertTrue(app.textFields["phone number"].exists)
        XCTAssertTrue(app.buttons["continue"].exists)
        XCTAssertFalse(app.buttons["request to join"].exists)
        XCTAssertFalse(app.staticTexts["request to join"].exists)
        XCTAssertFalse(app.secureTextFields["password"].exists)
    }
}
