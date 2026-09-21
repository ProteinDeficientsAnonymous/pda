import XCTest

final class GuestCalendarUITests: XCTestCase {
    func test_listOpensDetailAndHidesLocation() throws {
        let app = XCUIApplication()
        app.launchArguments = ["--reset-session"]
        app.launch()

        XCTAssertTrue(app.staticTexts["calendar"].waitForExistence(timeout: 20))

        let baked = app.staticTexts["free baked goods"]
        for _ in 0 ..< 12 where !baked.exists {
            app.swipeUp()
        }
        XCTAssertTrue(baked.waitForExistence(timeout: 5), "expected free baked goods in the guest list")
        baked.tap()

        XCTAssertTrue(app.staticTexts["want to see more?"].waitForExistence(timeout: 15))
        XCTAssertTrue(app.staticTexts["free baked goods"].exists)
        XCTAssertFalse(app.staticTexts["675 union street"].exists)
        XCTAssertFalse(app.staticTexts["675 Union street"].exists)
        XCTAssertFalse(app.staticTexts["Duncan"].exists)
        XCTAssertFalse(app.staticTexts["who’s going"].exists)
        XCTAssertFalse(app.staticTexts["who's going"].exists)
        XCTAssertFalse(app.buttons["rsvp"].exists)
        XCTAssertFalse(app.staticTexts["sign in"].exists)

        let dest = URL(
            fileURLWithPath: ProcessInfo.processInfo.environment["PDA_DEMO_SCREENSHOT"]
                ?? "/tmp/pda-slice-1-event-detail.png"
        )
        try XCUIScreen.main.screenshot().pngRepresentation.write(to: dest)
    }
}
