import XCTest

final class LoginUITests: XCTestCase {
    func test_signInIsPhoneThenPassword_lowercase_noJoin() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--reset-session"]
        app.launch()

        XCTAssertTrue(app.buttons["sign in"].waitForExistence(timeout: 20))
        app.buttons["sign in"].tap()

        XCTAssertTrue(app.staticTexts["welcome back"].waitForExistence(timeout: 5))
        XCTAssertTrue(app.staticTexts["sign in to your pda account"].exists)
        let phone = app.textFields["phone number"]
        XCTAssertTrue(phone.exists)
        phone.tap()
        phone.typeText("+15555550100")
        XCTAssertTrue(app.buttons["continue"].exists)
        app.buttons["continue"].tap()
        XCTAssertFalse(app.buttons["request to join"].exists)
        XCTAssertFalse(app.staticTexts["request to join"].exists)
    }
}
