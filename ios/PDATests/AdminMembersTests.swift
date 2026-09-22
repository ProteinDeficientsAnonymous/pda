import XCTest

@testable import PDA

final class AdminMembersTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func setUp() {
        super.setUp()
        MockHTTP.handler = nil
    }

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_adminMembersURL_isMembersListWithoutNonMembers() {
        let url = adminMembersURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/auth/users/")
        XCTAssertNil(url.query)
    }

    func test_adminMembers_getsListWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                [
                    "id": "u-1",
                    "full_name": "Ada Lovelace",
                    "phone_number": "+15555550100",
                    "email": "ada@pda.test",
                    "date_joined": "2026-01-01T00:00:00Z",
                    "roles": [["id": "r1", "name": "member", "is_default": true, "permissions": []]],
                    "is_paused": true,
                ],
            ])
        }
        let members = try await makeClient(tokens).adminMembers()
        XCTAssertEqual(members.map(\.id), ["u-1"])
        XCTAssertEqual(members[0].fullName, "Ada Lovelace")
        XCTAssertEqual(members[0].phoneNumber, "+15555550100")
        XCTAssertEqual(members[0].email, "ada@pda.test")
        XCTAssertEqual(adminMemberSubtitle(members[0]), "+15555550100")
    }

    func test_adminMembers_403WithoutManageUsers() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(routePath(request.url), "/api/auth/users/")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied", "field": NSNull()]]])
        }
        do {
            _ = try await makeClient().adminMembers()
            XCTFail("403 should not return the list")
        } catch AdminMembersError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminMembersModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminMembersModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.members.isEmpty)
        XCTAssertEqual(model.explanationTitle, AdminMembersCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, AdminMembersCopy.forbiddenBody)
    }

    func test_membersTile_opensAdminListOnly() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "manage_users",
            "manage_events",
            "approve_join_requests",
            "edit_join_questions",
            "manage_documents",
        ]))
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .members }.map(\.id), ["members"])
        XCTAssertEqual(
            tiles.filter { adminHubDestination(for: $0) == nil }.map(\.id),
            ["join-form", "docs"]
        )
    }

    func test_adminMembersCopy_isLowercase() {
        let blobs = [
            AdminMembersCopy.title,
            AdminMembersCopy.loading,
            AdminMembersCopy.error,
            AdminMembersCopy.empty,
            AdminMembersCopy.forbiddenTitle,
            AdminMembersCopy.forbiddenBody,
            AdminMembersCopy.fallbackName,
        ]
        XCTAssertEqual(AdminMembersCopy.title, "members")
        XCTAssertEqual(AdminMembersCopy.error, "couldn't load members — try refreshing")
        XCTAssertEqual(AdminMembersCopy.empty, "no members yet 🌿")
        XCTAssertEqual(AdminMembersCopy.forbiddenBody, "you need permission to manage users to see this list.")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func user(permissions: [String]) throws -> SessionUser {
        let payload: [String: Any] = [
            "id": "user-1",
            "is_member": true,
            "permissions": permissions,
            "roles": [],
        ]
        return try JSONDecoder().decode(SessionUser.self, from: JSONSerialization.data(withJSONObject: payload))
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
