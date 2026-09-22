import XCTest

@testable import PDA

final class AdminHubTests: XCTestCase {
    func test_noAdminPermission_hidesHub() throws {
        XCTAssertFalse(hasAnyAdminPermission(nil))
        XCTAssertFalse(hasAnyAdminPermission(try user()))
        XCTAssertFalse(hasAnyAdminPermission(try user(permissions: ["edit_faq", "manage_feature_flags"])))
        XCTAssertTrue(hasAnyAdminPermission(try user(permissions: ["manage_surveys"])))
        XCTAssertTrue(adminHubTiles(for: try user(permissions: ["edit_faq"])).isEmpty)
        XCTAssertTrue(adminHubTiles(for: nil).isEmpty)
    }

    func test_subsetPermission_showsOnlyMatchingTiles() throws {
        XCTAssertEqual(adminHubTiles(for: try user(permissions: ["manage_users"])).map(\.label), ["members"])
        XCTAssertEqual(
            adminHubTiles(for: try user(permissions: ["approve_join_requests"])).map(\.label),
            ["join requests"]
        )
        XCTAssertEqual(
            adminHubTiles(for: try user(permissions: ["manage_events"])).map(\.label),
            ["events", "flagged events", "attendance"]
        )
        XCTAssertEqual(
            adminHubTiles(for: try user(permissions: ["edit_join_questions"])).map(\.label),
            ["join form"]
        )
        XCTAssertEqual(adminHubTiles(for: try user(permissions: ["manage_documents"])).map(\.label), ["docs"])
        XCTAssertFalse(
            adminHubTiles(for: try user(permissions: ["manage_events"])).map(\.label).contains("surveys")
        )
        XCTAssertFalse(
            adminHubTiles(for: try user(permissions: ["manage_events"])).map(\.label).contains("feature flags")
        )
    }

    func test_rolesPayload_grantsJoinRequestsTile() throws {
        let vetter = try user(roles: [
            ["name": "vetter", "is_default": false, "permissions": ["approve_join_requests"]],
        ])
        XCTAssertTrue(hasAnyAdminPermission(vetter))
        XCTAssertEqual(adminHubTiles(for: vetter).map(\.label), ["join requests"])
    }

    func test_defaultAdminRole_showsSubsetTiles() throws {
        let admin = try user(roles: [
            ["name": "admin", "is_default": true, "permissions": []],
        ])
        XCTAssertEqual(
            adminHubTiles(for: admin).map(\.label),
            ["members", "join requests", "events", "flagged events", "attendance", "surveys", "join form", "docs"]
        )
        let namedOnly = try user(roles: [
            ["name": "admin", "is_default": false, "permissions": []],
        ])
        XCTAssertFalse(hasAnyAdminPermission(namedOnly))
    }

    func test_adminHubCopy_matchesWebAndIsLowercase() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "manage_users",
            "approve_join_requests",
            "manage_events",
            "edit_join_questions",
            "manage_documents",
        ]))
        XCTAssertEqual(tiles.map(\.detail), [
            "create, edit, pause, or reset accounts",
            "approve or reject incoming applications",
            "review drafts, past, and cancelled events",
            "review and action flags from members",
            "who came to events and when",
            "edit the questions asked on /join",
            "manage the shared document library",
        ])
        let blobs = [AdminHubCopy.title] + tiles.flatMap { [$0.label, $0.detail] }
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func user(permissions: [String] = [], roles: [[String: Any]] = []) throws -> SessionUser {
        let payload: [String: Any] = [
            "id": "user-1",
            "phone_number": "+15555550100",
            "full_name": "ada",
            "is_member": true,
            "permissions": permissions,
            "roles": roles,
        ]
        return try JSONDecoder().decode(SessionUser.self, from: JSONSerialization.data(withJSONObject: payload))
    }
}
