import XCTest

@testable import PDA

final class AdminMemberDetailTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func setUp() {
        super.setUp()
        MockHTTP.handler = nil
    }

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_adminMemberDetail_getsMatchingUserFromMembersList() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                adminMemberJSON(id: "u-1", name: "Bea", phone: "+15555550101", email: "bea@pda.test", bio: ""),
                adminMemberJSON(id: "u-2", name: "Ada Lovelace", phone: "+15555550100", email: "ada@pda.test", bio: "vegan potlucks"),
            ])
        }
        let member = try await makeClient(tokens).adminMemberDetail(id: "u-2")
        XCTAssertEqual(member.id, "u-2")
        XCTAssertEqual(member.fullName, "Ada Lovelace")
        XCTAssertEqual(member.phoneNumber, "+15555550100")
        XCTAssertEqual(member.email, "ada@pda.test")
        XCTAssertEqual(member.bio, "vegan potlucks")
        XCTAssertEqual(adminMemberDetailTitle(member), "Ada Lovelace")
    }

    func test_adminMemberDetail_403WithoutManageUsers() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().adminMemberDetail(id: "u-1")
            XCTFail("403 should not return a member")
        } catch AdminMembersError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminMemberDetail_missingUserIsNotFound() async throws {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, [
                adminMemberJSON(id: "u-1", name: "Bea", phone: "", email: "", bio: ""),
            ])
        }
        do {
            _ = try await makeClient().adminMemberDetail(id: "missing")
            XCTFail("missing member should not return")
        } catch AdminMembersError.notFound {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminMemberDetailModel_forbiddenShowsExplanationNotMember() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-1")
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.member)
        XCTAssertEqual(model.explanationTitle, AdminMembersCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, AdminMembersCopy.forbiddenBody)
    }

    func test_pauseMemberURL_keepsTrailingSlash() {
        let url = pauseMemberURL(base: base, id: "u-2")
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/auth/users/u-2/")
        XCTAssertNil(url.query)
    }

    func test_pauseMember_patchesOnlyIsPaused() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    pauseMemberJSON(id: "u-2", name: "Ada", paused: false, admin: false),
                ])
            }
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/u-2/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let raw = String(data: request.httpBody ?? Data(), encoding: .utf8)
            XCTAssertEqual(raw, "{\"is_paused\":true}")
            return MockHTTP.json(200, ["id": "u-2", "is_paused": true])
        }
        let model = AdminMemberDetailModel(client: makeClient(tokens))
        await model.load(id: "u-2")
        XCTAssertFalse(model.paused)
        let saved = await model.setPaused(true)
        XCTAssertTrue(saved)
        XCTAssertTrue(model.paused)
        XCTAssertEqual(model.toast, "member paused ✓")
    }

    func test_unpauseMember_patchesFalse() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    pauseMemberJSON(id: "u-2", name: "Ada", paused: true, admin: false),
                ])
            }
            let raw = String(data: request.httpBody ?? Data(), encoding: .utf8)
            XCTAssertEqual(raw, "{\"is_paused\":false}")
            return MockHTTP.json(200, ["id": "u-2", "is_paused": false])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        XCTAssertTrue(model.paused)
        let saved = await model.setPaused(false)
        XCTAssertTrue(saved)
        XCTAssertFalse(model.paused)
        XCTAssertEqual(model.toast, "member unpaused ✓")
    }

    func test_pauseMember_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    pauseMemberJSON(id: "u-2", name: "Ada", paused: false, admin: false),
                ])
            }
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        let saved = await model.setPaused(true)
        XCTAssertFalse(saved)
        XCTAssertFalse(model.paused)
        XCTAssertNil(model.toast)
        XCTAssertTrue(model.pauseForbidden)
        XCTAssertEqual(model.pauseExplanationTitle, PauseAccountCopy.forbiddenTitle)
        XCTAssertEqual(model.pauseExplanationBody, "you need permission to manage users to pause this account.")
    }

    func test_pauseMember_selfRejectionLeavesToggle() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    pauseMemberJSON(id: "u-2", name: "Ada", paused: false, admin: false),
                ])
            }
            return MockHTTP.json(400, ["detail": [["code": "user.cannot_pause_self"]]])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        let saved = await model.setPaused(true)
        XCTAssertFalse(saved)
        XCTAssertFalse(model.paused)
        XCTAssertNil(model.toast)
        XCTAssertFalse(model.pauseForbidden)
        XCTAssertEqual(model.formError, "you can't pause your own account")
    }

    func test_pauseMember_adminDoesNotPatch() async {
        var patched = false
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                patched = true
            }
            return MockHTTP.json(200, [
                pauseMemberJSON(id: "u-2", name: "Ada", paused: false, admin: true),
            ])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        XCTAssertTrue(memberIsDefaultAdmin(model.member!))
        let saved = await model.setPaused(true)
        XCTAssertFalse(saved)
        XCTAssertFalse(patched)
        XCTAssertFalse(model.paused)
        XCTAssertNil(model.toast)
        XCTAssertEqual(PauseAccountCopy.adminsCantBePaused, "admins can't be paused")
    }

    func test_showsPauseAccount_requiresManageUsers() throws {
        XCTAssertFalse(showsPauseAccount(try viewer(permissions: ["approve_join_requests"])))
        XCTAssertTrue(showsPauseAccount(try viewer(permissions: ["manage_users"])))
        XCTAssertTrue(showsPauseAccount(try viewer(permissions: [], admin: true)))
        XCTAssertFalse(showsPauseAccount(nil))
        XCTAssertEqual(PauseAccountCopy.label, "pause account")
    }

    func test_pauseAccountCopy_isLowercase() {
        let blobs = [
            PauseAccountCopy.label,
            PauseAccountCopy.paused,
            PauseAccountCopy.unpaused,
            PauseAccountCopy.adminsCantBePaused,
            PauseAccountCopy.cannotPauseSelf,
            PauseAccountCopy.forbiddenTitle,
            PauseAccountCopy.forbiddenBody,
        ]
        XCTAssertEqual(PauseAccountCopy.paused, "member paused ✓")
        XCTAssertEqual(PauseAccountCopy.unpaused, "member unpaused ✓")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_magicLoginURL_keepsTrailingSlash() {
        let url = magicLoginLinkURL(base: base, id: "u-2")
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/auth/users/u-2/magic-link/")
        XCTAssertNil(url.query)
    }

    func test_generateMagicLoginLink_postsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    magicMemberJSON(id: "u-2", firstName: "Ada"),
                ])
            }
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/u-2/magic-link/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            XCTAssertTrue(request.httpBody == nil || request.httpBody?.isEmpty == true)
            return MockHTTP.json(200, [
                "detail": "Magic login link generated.",
                "magic_link_token": "tok",
            ])
        }
        let model = AdminMemberDetailModel(client: makeClient(tokens))
        await model.load(id: "u-2")
        XCTAssertEqual(magicLoginButtonLabel(working: false), "generate magic login link")
        XCTAssertEqual(magicLoginButtonLabel(working: true), "working…")
        let generated = await model.generateMagicLink()
        XCTAssertTrue(generated)
        XCTAssertFalse(model.magicWorking)
        XCTAssertEqual(model.magicLink, "https://pda.test/magic-login/tok")
        XCTAssertEqual(model.magicCopyLabel, "copy link")
        model.copyMagicLink()
        XCTAssertEqual(model.magicCopyLabel, "copied ✓")
        XCTAssertEqual(
            model.welcomeMessage,
            "hi ada 🌱 welcome to pda! use this link to sign in: https://pda.test/magic-login/tok"
        )
        XCTAssertTrue(model.smsLink.hasPrefix("sms:+15555550100&body="))
        XCTAssertFalse(model.smsLink.contains("?body="))
        XCTAssertTrue(model.smsLink.contains("hi%20ada"))
        XCTAssertTrue(model.smsLink.contains("%3A%2F%2Fpda.test%2Fmagic-login%2Ftok"))
    }

    func test_generateMagicLoginLink_emptyFirstNameUsesHiSeedling() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    magicMemberJSON(id: "u-2", firstName: "  "),
                ])
            }
            return MockHTTP.json(200, ["detail": "ok", "magic_link_token": "tok"])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        _ = await model.generateMagicLink()
        XCTAssertEqual(
            model.welcomeMessage,
            "hi 🌱 welcome to pda! use this link to sign in: https://pda.test/magic-login/tok"
        )
    }

    func test_generateMagicLoginLink_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, [
                    magicMemberJSON(id: "u-2", firstName: "Ada"),
                ])
            }
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        let generated = await model.generateMagicLink()
        XCTAssertFalse(generated)
        XCTAssertNil(model.magicLink)
        XCTAssertTrue(model.magicForbidden)
        XCTAssertEqual(model.magicExplanationTitle, MagicLoginCopy.forbiddenTitle)
        XCTAssertEqual(model.magicExplanationBody, "you need permission to manage users to generate a login link.")
    }

    func test_showsMagicLoginLink_requiresManageUsers() throws {
        XCTAssertFalse(showsMagicLoginLink(try viewer(permissions: ["approve_join_requests"])))
        XCTAssertTrue(showsMagicLoginLink(try viewer(permissions: ["manage_users"])))
        XCTAssertTrue(showsMagicLoginLink(try viewer(permissions: [], admin: true)))
        XCTAssertFalse(showsMagicLoginLink(nil))
        XCTAssertEqual(
            MagicLoginCopy.hint,
            "resets password flow for this member and generates a one-time login url for you to send them."
        )
    }

    func test_magicLoginCopy_isLowercase() {
        let blobs = [
            MagicLoginCopy.button,
            MagicLoginCopy.working,
            MagicLoginCopy.copyLink,
            MagicLoginCopy.copied,
            MagicLoginCopy.sendWelcome,
            MagicLoginCopy.hint,
            MagicLoginCopy.forbiddenTitle,
            MagicLoginCopy.forbiddenBody,
        ]
        XCTAssertEqual(MagicLoginCopy.copied, "copied ✓")
        XCTAssertEqual(MagicLoginCopy.working, "working…")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_adminMemberDetailCopy_isLowercase() {
        let blobs = [
            AdminMemberDetailCopy.notFound,
            AdminMemberDetailCopy.error,
            AdminMemberDetailCopy.bio,
        ]
        XCTAssertEqual(AdminMemberDetailCopy.notFound, "member not found")
        XCTAssertEqual(AdminMemberDetailCopy.error, "couldn't load members — try refreshing")
        XCTAssertEqual(AdminMemberDetailCopy.bio, "bio")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func viewer(permissions: [String], admin: Bool = false) throws -> SessionUser {
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

private func adminMemberJSON(id: String, name: String, phone: String, email: String, bio: String) -> [String: Any] {
    [
        "id": id,
        "full_name": name,
        "phone_number": phone,
        "email": email,
        "bio": bio,
        "date_joined": "2026-01-01T00:00:00Z",
        "roles": [],
    ]
}

private func pauseMemberJSON(id: String, name: String, paused: Bool, admin: Bool) -> [String: Any] {
    var row = adminMemberJSON(id: id, name: name, phone: "+15555550100", email: "ada@pda.test", bio: "")
    row["is_paused"] = paused
    if admin {
        row["roles"] = [["id": "r-admin", "name": "admin", "is_default": true, "permissions": []]]
    }
    return row
}

private func magicMemberJSON(id: String, firstName: String) -> [String: Any] {
    var row = adminMemberJSON(id: id, name: "Ada Lovelace", phone: "+15555550100", email: "ada@pda.test", bio: "")
    row["first_name"] = firstName
    return row
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
