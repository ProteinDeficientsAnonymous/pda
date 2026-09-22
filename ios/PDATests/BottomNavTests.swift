import XCTest

@testable import PDA

final class BottomNavTests: XCTestCase {
    func test_bottomNavLabels_matchWebAndAreLowercase() {
        XCTAssertEqual(
            BottomNavCopy.items,
            ["calendar", "my rsvps", "add event", "members", "profile"]
        )
        XCTAssertEqual(BottomNavCopy.items, BottomNavCopy.items.map { $0.lowercased() })
    }

    func test_bottomNav_myRsvpsFollowsAuthAndGuestToken() throws {
        XCTAssertEqual(
            bottomNavRoute(.myRsvps, user: nil, hasGuestToken: false),
            .login
        )
        XCTAssertEqual(
            bottomNavRoute(.myRsvps, user: nil, hasGuestToken: true),
            .guestRsvps
        )
        XCTAssertEqual(
            bottomNavRoute(.myRsvps, user: try user(), hasGuestToken: false),
            .myEvents
        )
        XCTAssertEqual(
            bottomNavRoute(.myRsvps, user: try user(), hasGuestToken: true),
            .myEvents
        )
    }

    func test_bottomNav_routesExistingScreens() throws {
        let member = try user()
        XCTAssertEqual(bottomNavRoute(.calendar, user: nil, hasGuestToken: false), .calendar)
        XCTAssertEqual(bottomNavRoute(.members, user: nil, hasGuestToken: false), .login)
        XCTAssertEqual(bottomNavRoute(.members, user: member, hasGuestToken: false), .members)
        XCTAssertEqual(bottomNavRoute(.addEvent, user: nil, hasGuestToken: false), .login)
        XCTAssertEqual(bottomNavRoute(.addEvent, user: member, hasGuestToken: false), .addEvent)
        XCTAssertEqual(bottomNavRoute(.profile, user: nil, hasGuestToken: false), .login)
        XCTAssertEqual(bottomNavRoute(.profile, user: member, hasGuestToken: false), .profile)
    }

    func test_bottomNav_tentativeMemberSeesExistingLock() throws {
        let tentative = try user(isMember: false)
        XCTAssertEqual(
            bottomNavRoute(.members, user: tentative, hasGuestToken: false),
            .locked(title: MemberLockCopy.directoryTitle, body: MemberLockCopy.directoryBody)
        )
        XCTAssertEqual(
            bottomNavRoute(.addEvent, user: tentative, hasGuestToken: false),
            .locked(title: MemberLockCopy.addEventTitle, body: MemberLockCopy.addEventBody)
        )
        XCTAssertEqual(bottomNavRoute(.profile, user: tentative, hasGuestToken: false), .profile)
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
