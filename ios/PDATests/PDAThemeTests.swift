import XCTest

@testable import PDA

final class PDAThemeTests: XCTestCase {
    func test_lightModeHex_matchesIndexCss() {
        XCTAssertEqual(PDAPalette.background.light, "#f7fbf1")
        XCTAssertEqual(PDAPalette.foreground.light, "#191d17")
        XCTAssertEqual(PDAPalette.brand600.light, "#3c6939")
        XCTAssertEqual(PDAPalette.brand700.light, "#245024")
        XCTAssertEqual(PDAPalette.destructive.light, "#dc2626")
    }
}
