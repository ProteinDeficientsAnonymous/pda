import XCTest

@testable import PDA

final class MenuSheetTests: XCTestCase {
    func test_menuSheetItems_matchWebOrderOmitInstallAndAreLowercase() throws {
        let guest = [
            MenuSheetEntry(label: "home", route: .home),
            MenuSheetEntry(label: "faq", route: .faq),
            MenuSheetEntry(label: "donate", route: .donate),
        ]
        let signedIn = guest + [
            MenuSheetEntry(label: "guidelines", route: .guidelines),
            MenuSheetEntry(label: "volunteer", route: .volunteer),
            MenuSheetEntry(label: "settings", route: .settings),
            MenuSheetEntry(label: "log out", route: .logOut),
        ]
        XCTAssertEqual(menuSheetItems(user: nil), guest)
        XCTAssertEqual(menuSheetItems(user: try user()), signedIn)
        XCTAssertEqual(menuSheetItems(user: try user(isMember: false)), signedIn)
        let labels = signedIn.map(\.label)
        XCTAssertEqual(labels, labels.map { $0.lowercased() })
        XCTAssertFalse(labels.contains("install app"))
    }

    private func user(isMember: Bool = true) throws -> SessionUser {
        try Event.decoder.decode(
            SessionUser.self,
            from: Data("""
            {"id":"user-1","first_name":"ada","email":"ada@pda.test","is_member":\(isMember)}
            """.utf8)
        )
    }
}
