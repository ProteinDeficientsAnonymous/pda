import XCTest

@testable import PDA

final class CreateRoleTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_rolePermissionChoices_matchWebLabels() {
        XCTAssertEqual(rolePermissionChoices.map(\.key), [
            "create_user",
            "manage_users",
            "manage_roles",
            "approve_join_requests",
            "manage_events",
            "edit_guidelines",
            "edit_faq",
            "edit_homepage",
            "edit_join_questions",
            "manage_surveys",
            "tag_official_event",
            "tag_club_event",
            "manage_documents",
            "manage_feature_flags",
        ])
        XCTAssertEqual(rolePermissionChoices.map(\.label), [
            "create users",
            "manage users",
            "manage roles",
            "approve join requests",
            "manage events",
            "edit guidelines",
            "edit faq",
            "edit homepage",
            "edit join questions",
            "manage surveys",
            "tag official events",
            "tag club events",
            "manage documents",
            "manage feature flags",
        ])
        XCTAssertEqual(roleNameMaxLength, 40)
        XCTAssertEqual(clampedRoleName(String(repeating: "a", count: 41)).count, 40)
        XCTAssertEqual(CreateRoleCopy.button, "add role")
        XCTAssertEqual(CreateRoleCopy.title, "create role")
        XCTAssertEqual(CreateRoleCopy.name, "name")
        XCTAssertEqual(CreateRoleCopy.placeholder, "e.g. greeter")
        XCTAssertEqual(CreateRoleCopy.permissions, "permissions")
    }

    func test_createRole_postsTrimmedNameAndPermissions() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/auth/roles/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: Any]
            XCTAssertEqual(body?["name"] as? String, "greeter")
            XCTAssertEqual(body?["permissions"] as? [String], ["manage_events", "edit_faq"])
            return MockHTTP.json(201, roleJSON(id: "r-new", name: "greeter", permissions: ["manage_events", "edit_faq"], users: 0))
        }
        let model = CreateRoleModel(client: makeClient(tokens))
        model.name = "  greeter  "
        model.togglePermission("manage_events")
        model.togglePermission("edit_faq")
        model.togglePermission("edit_faq")
        model.togglePermission("edit_faq")
        let created = await model.submit()
        XCTAssertTrue(created)
        XCTAssertTrue(model.closed)
        XCTAssertEqual(model.created?.id, "r-new")
        XCTAssertEqual(adminRoleName(model.created!), "greeter")
    }

    func test_createRole_clampsNameToFortyCharacters() async throws {
        MockHTTP.handler = { request in
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: Any]
            XCTAssertEqual((body?["name"] as? String)?.count, 40)
            return MockHTTP.json(201, roleJSON(id: "r-long", name: String(repeating: "a", count: 40), permissions: [], users: 0))
        }
        let model = CreateRoleModel(client: makeClient())
        model.name = String(repeating: "a", count: 41)
        let created = await model.submit()
        XCTAssertTrue(created)
    }

    func test_createRole_emptyNameDoesNotPost() async {
        var posted = false
        MockHTTP.handler = { _ in
            posted = true
            return MockHTTP.json(201, roleJSON(id: "r", name: "x", permissions: [], users: 0))
        }
        let blank = CreateRoleModel(client: makeClient())
        blank.name = "   "
        let blankCreated = await blank.submit()
        XCTAssertFalse(blankCreated)
        XCTAssertEqual(blank.formError, "role name is required")
        XCTAssertFalse(blank.closed)
        XCTAssertFalse(posted)
    }

    func test_createRole_403ShowsExplanation() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = CreateRoleModel(client: makeClient())
        model.name = "greeter"
        let created = await model.submit()
        XCTAssertFalse(created)
        XCTAssertFalse(model.closed)
        XCTAssertNil(model.created)
        XCTAssertTrue(model.forbidden)
        XCTAssertEqual(model.explanationTitle, CreateRoleCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, "you need permission to manage roles to create a role.")
    }

    func test_createRole_serverFailureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = CreateRoleModel(client: makeClient())
        model.name = "greeter"
        let created = await model.submit()
        XCTAssertFalse(created)
        XCTAssertFalse(model.closed)
        XCTAssertEqual(model.formError, "something went wrong — try again")
    }

    func test_createRole_cancelDoesNotPost() {
        var posted = false
        MockHTTP.handler = { _ in
            posted = true
            return MockHTTP.json(201, roleJSON(id: "r", name: "x", permissions: [], users: 0))
        }
        let model = CreateRoleModel(client: makeClient())
        model.name = "greeter"
        model.togglePermission("manage_events")
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertNil(model.created)
        XCTAssertFalse(posted)
    }

    func test_createRole_successCanAppearInList() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "POST" {
                return MockHTTP.json(201, roleJSON(id: "r-new", name: "greeter", permissions: [], users: 0))
            }
            return MockHTTP.json(200, [
                roleJSON(id: "r-new", name: "greeter", permissions: [], users: 0),
            ])
        }
        let form = CreateRoleModel(client: makeClient())
        form.name = "greeter"
        let created = await form.submit()
        XCTAssertTrue(created)
        let listed = AdminRolesModel(client: makeClient())
        await listed.load()
        XCTAssertEqual(listed.roles.map(adminRoleName), ["greeter"])
    }

    func test_createRoleCopy_isLowercase() {
        let blobs = [
            CreateRoleCopy.button,
            CreateRoleCopy.title,
            CreateRoleCopy.name,
            CreateRoleCopy.placeholder,
            CreateRoleCopy.permissions,
            CreateRoleCopy.cancel,
            CreateRoleCopy.create,
            CreateRoleCopy.saving,
            CreateRoleCopy.nameRequired,
            CreateRoleCopy.failure,
            CreateRoleCopy.forbiddenTitle,
            CreateRoleCopy.forbiddenBody,
        ] + rolePermissionChoices.map(\.label)
        XCTAssertEqual(CreateRoleCopy.nameRequired, "role name is required")
        XCTAssertEqual(CreateRoleCopy.failure, "something went wrong — try again")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
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
