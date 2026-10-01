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

    func test_showsRoleDelete_hidesAdminAndMember() {
        XCTAssertFalse(showsRoleDelete(AdminRole(id: "a", name: "admin", permissions: [], userCount: 1)))
        XCTAssertFalse(showsRoleDelete(AdminRole(id: "m", name: "Member", permissions: [], userCount: 0)))
        XCTAssertTrue(showsRoleDelete(AdminRole(id: "g", name: "greeter", permissions: [], userCount: 0)))
        XCTAssertEqual(RoleDeleteCopy.button, "delete")
        XCTAssertEqual(RoleDeleteCopy.title, "delete role")
        XCTAssertEqual(RoleDeleteCopy.confirm, "delete")
    }

    func test_roleDeleteMessage_matchesMemberCount() {
        let none = AdminRole(id: "g", name: "Greeter", permissions: [], userCount: 0)
        let one = AdminRole(id: "g", name: "Greeter", permissions: [], userCount: 1)
        let many = AdminRole(id: "g", name: "Greeter", permissions: [], userCount: 3)
        XCTAssertEqual(roleDeleteMessage(none), "delete the \"greeter\" role? this cannot be undone.")
        XCTAssertEqual(roleDeleteMessage(one), "1 member has the \"greeter\" role — deleting will remove it from them. continue?")
        XCTAssertEqual(roleDeleteMessage(many), "3 members have the \"greeter\" role — deleting will remove it from all of them. continue?")
        XCTAssertEqual(roleDeleteToast(none), "greeter deleted ✓")
    }

    func test_deleteRole_cancelDoesNotCallAPI() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(204, [:])
        }
        let model = AdminRolesModel(client: makeClient())
        let role = AdminRole(id: "g", name: "greeter", permissions: [], userCount: 0)
        let prompt = model.prepareDelete(role)
        XCTAssertEqual(prompt?.title, "delete role")
        XCTAssertEqual(prompt?.confirmLabel, "delete")
        XCTAssertEqual(prompt?.message, roleDeleteMessage(role))
        model.cancelDelete()
        let deleted = await model.commitDelete()
        XCTAssertFalse(deleted)
        XCTAssertFalse(called)
        XCTAssertNil(model.toast)
    }

    func test_deleteRole_sendsDeleteAndRemovesRow() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    roleJSON(id: "g", name: "Greeter", permissions: [], users: 0),
                    roleJSON(id: "h", name: "Host", permissions: ["manage_events"], users: 2),
                ])
            }
            XCTAssertEqual(request.httpMethod, "DELETE")
            XCTAssertEqual(routePath(request.url), "/api/auth/roles/g/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            XCTAssertTrue(request.httpBody == nil || request.httpBody?.isEmpty == true)
            return MockHTTP.json(204, [:])
        }
        let model = AdminRolesModel(client: makeClient(tokens))
        await model.load()
        let role = model.roles[0]
        _ = model.prepareDelete(role)
        let deleted = await model.commitDelete()
        XCTAssertTrue(deleted)
        XCTAssertEqual(model.roles.map(\.id), ["h"])
        XCTAssertEqual(model.toast, "greeter deleted ✓")
    }

    func test_deleteRole_403ShowsExplanation() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminRolesModel(client: makeClient())
        let role = AdminRole(id: "g", name: "greeter", permissions: [], userCount: 2)
        model.roles = [role]
        _ = model.prepareDelete(role)
        let deleted = await model.commitDelete()
        XCTAssertFalse(deleted)
        XCTAssertEqual(model.roles.map(\.id), ["g"])
        XCTAssertNil(model.toast)
        XCTAssertTrue(model.deleteForbidden)
        XCTAssertEqual(model.deleteExplanationTitle, "delete role")
        XCTAssertEqual(model.deleteExplanationBody, "you need permission to manage roles to delete this role.")
    }

    func test_deleteRole_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = AdminRolesModel(client: makeClient())
        let role = AdminRole(id: "g", name: "greeter", permissions: [], userCount: 0)
        model.roles = [role]
        _ = model.prepareDelete(role)
        let deleted = await model.commitDelete()
        XCTAssertFalse(deleted)
        XCTAssertEqual(model.roles.map(\.id), ["g"])
        XCTAssertEqual(model.deleteError, "couldn't delete role — try again")
    }

    func test_deleteRole_protectedNameDoesNotPrepare() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(204, [:])
        }
        let model = AdminRolesModel(client: makeClient())
        XCTAssertNil(model.prepareDelete(AdminRole(id: "a", name: "admin", permissions: [], userCount: 1)))
        let deleted = await model.commitDelete()
        XCTAssertFalse(deleted)
        XCTAssertFalse(called)
    }

    func test_roleDeleteCopy_isLowercase() {
        let blobs = [
            RoleDeleteCopy.button,
            RoleDeleteCopy.title,
            RoleDeleteCopy.confirm,
            RoleDeleteCopy.cancel,
            RoleDeleteCopy.failure,
            RoleDeleteCopy.forbiddenTitle,
            RoleDeleteCopy.forbiddenBody,
            roleDeleteMessage(AdminRole(id: "g", name: "greeter", permissions: [], userCount: 0)),
            roleDeleteMessage(AdminRole(id: "g", name: "greeter", permissions: [], userCount: 1)),
            roleDeleteToast(AdminRole(id: "g", name: "Greeter", permissions: [], userCount: 0)),
        ]
        XCTAssertEqual(RoleDeleteCopy.failure, "couldn't delete role — try again")
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
