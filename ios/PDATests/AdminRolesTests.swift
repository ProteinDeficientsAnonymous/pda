import XCTest

@testable import PDA

final class AdminRolesTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_adminRolesURL_keepsTrailingSlash() {
        let url = adminRolesURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/auth/roles/")
        XCTAssertNil(url.query)
    }

    func test_adminRoles_getsListWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/auth/roles/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                roleJSON(id: "r1", name: "Host", permissions: ["manage_events"], users: 1),
                roleJSON(id: "r2", name: "Greeter", permissions: [], users: 0),
            ])
        }
        let rows = try await makeClient(tokens).adminRoles()
        XCTAssertEqual(rows.map(\.id), ["r1", "r2"])
        XCTAssertEqual(adminRoleName(rows[0]), "host")
        XCTAssertEqual(adminRoleSubtitle(rows[0]), "1 permission · 1 member")
        XCTAssertEqual(adminRoleSubtitle(rows[1]), "no permissions · no members")
    }

    func test_adminRoleSubtitle_pluralizesCounts() {
        let role = AdminRole(id: "r3", name: "crew", permissions: ["a", "b"], userCount: 3)
        XCTAssertEqual(adminRoleSubtitle(role), "2 permissions · 3 members")
    }

    func test_adminRoles_403WithoutManageRoles() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().adminRoles()
            XCTFail("403 should not return roles")
        } catch AdminRolesError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminRolesModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminRolesModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.roles.isEmpty)
        XCTAssertEqual(model.explanationTitle, AdminRolesCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, AdminRolesCopy.forbiddenBody)
    }

    func test_rolesTab_showsOnlyWithManageRoles() throws {
        XCTAssertEqual(adminMembersTabs(showRoles: false), ["members"])
        XCTAssertEqual(adminMembersTabs(showRoles: true), ["members", "roles"])
        XCTAssertFalse(showsAdminRolesTab(try user(permissions: ["manage_users"])))
        XCTAssertTrue(showsAdminRolesTab(try user(permissions: ["manage_roles"])))
        XCTAssertTrue(showsAdminRolesTab(try user(permissions: [], admin: true)))
    }

    func test_adminRolesCopy_isLowercase() {
        let blobs = [
            AdminRolesCopy.title,
            AdminRolesCopy.loading,
            AdminRolesCopy.error,
            AdminRolesCopy.empty,
            AdminRolesCopy.forbiddenTitle,
            AdminRolesCopy.forbiddenBody,
        ]
        XCTAssertEqual(AdminRolesCopy.empty, "no roles yet")
        XCTAssertEqual(AdminRolesCopy.error, "couldn't load roles — try refreshing")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func user(permissions: [String], admin: Bool = false) throws -> SessionUser {
        let roles: [[String: Any]] = admin
            ? [["name": "admin", "is_default": true, "permissions": []]]
            : []
        let payload: [String: Any] = [
            "id": "user-1",
            "is_member": true,
            "permissions": permissions,
            "roles": roles,
        ]
        return try JSONDecoder().decode(SessionUser.self, from: JSONSerialization.data(withJSONObject: payload))
    }
}

private func roleJSON(id: String, name: String, permissions: [String], users: Int) -> [String: Any] {
    [
        "id": id,
        "name": name,
        "is_default": false,
        "permissions": permissions,
        "user_count": users,
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
