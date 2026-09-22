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

    func test_showsMemberProfileEdit_onlyWithManageUsers() throws {
        XCTAssertFalse(showsMemberProfileEdit(nil))
        XCTAssertFalse(showsMemberProfileEdit(try viewer(permissions: ["edit_faq"])))
        XCTAssertTrue(showsMemberProfileEdit(try viewer(permissions: ["manage_users"])))
        XCTAssertTrue(showsMemberProfileEdit(try viewer(permissions: [], admin: true)))
    }

    func test_updateMemberProfile_patchesChangedFields() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTAssertEqual(routePath(request.url), "/api/auth/users/u-2/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                let patch = try JSONDecoder().decode(MemberProfilePatchBody.self, from: request.httpBody ?? Data())
                XCTAssertEqual(patch.first_name, "grace")
                XCTAssertEqual(patch.last_name, "hopper")
                XCTAssertNil(patch.phone_number)
                XCTAssertNil(patch.email)
                XCTAssertNil(patch.is_paused)
                XCTAssertNil(patch.has_joined_whatsapp)
                var saved = adminMemberJSON(id: "u-2", name: "Grace Hopper", phone: "+15555550100", email: "ada@pda.test", bio: "")
                saved["first_name"] = "grace"
                saved["last_name"] = "hopper"
                return MockHTTP.json(200, saved)
            }
            return MockHTTP.json(200, [self.profileMemberJSON()])
        }
        let model = AdminMemberDetailModel(client: makeClient(tokens))
        await model.load(id: "u-2")
        model.beginProfileEdit()
        XCTAssertEqual(model.profileFirstName, "ada")
        XCTAssertEqual(model.profileLastName, "lovelace")
        model.profileFirstName = "grace"
        model.profileLastName = "hopper"
        await model.saveProfile()
        XCTAssertFalse(model.editingProfile)
        XCTAssertEqual(model.member?.firstName, "grace")
        XCTAssertEqual(model.member?.lastName, "hopper")
        XCTAssertEqual(model.toast, "member updated ✓")
        XCTAssertNil(model.profileError)
    }

    func test_updateMemberProfile_requiresFirstName() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTFail("blank first name should not patch")
            }
            return MockHTTP.json(200, [self.profileMemberJSON()])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        model.beginProfileEdit()
        model.profileFirstName = "  "
        await model.saveProfile()
        XCTAssertTrue(model.editingProfile)
        XCTAssertEqual(model.profileError, "first name required")
        XCTAssertEqual(model.member?.firstName, "ada")
    }

    func test_updateMemberProfile_skipsUnchangedSave() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTFail("unchanged profile should not patch")
            }
            return MockHTTP.json(200, [self.profileMemberJSON()])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        model.beginProfileEdit()
        await model.saveProfile()
        XCTAssertFalse(model.editingProfile)
        XCTAssertNil(model.toast)
        XCTAssertEqual(model.member?.firstName, "ada")
    }

    func test_updateMemberProfile_403WithoutManageUsers() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "update_user"]]])
            }
            return MockHTTP.json(200, [self.profileMemberJSON()])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        model.beginProfileEdit()
        model.profileEmail = "new@pda.test"
        await model.saveProfile()
        XCTAssertEqual(model.member?.email, "ada@pda.test")
        XCTAssertEqual(model.member?.firstName, "ada")
        XCTAssertTrue(model.editingProfile)
        XCTAssertEqual(model.profileError, "couldn't save changes — try again")
    }

    func test_updateMemberProfile_skipsPauseForDefaultAdmin() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                let patch = try JSONDecoder().decode(MemberProfilePatchBody.self, from: request.httpBody ?? Data())
                XCTAssertNil(patch.is_paused)
                XCTAssertEqual(patch.email, "new@pda.test")
                var saved = self.profileMemberJSON()
                saved["email"] = "new@pda.test"
                saved["roles"] = [["id": "r-admin", "name": "admin", "is_default": true, "permissions": []]]
                return MockHTTP.json(200, saved)
            }
            var row = self.profileMemberJSON()
            row["roles"] = [["id": "r-admin", "name": "admin", "is_default": true, "permissions": []]]
            return MockHTTP.json(200, [row])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        model.beginProfileEdit()
        model.profilePaused = true
        model.profileEmail = "new@pda.test"
        await model.saveProfile()
        XCTAssertEqual(model.member?.email, "new@pda.test")
        XCTAssertFalse(model.member?.isPaused ?? true)
    }

    func test_memberProfileEditCopy_isLowercase() {
        let blobs = [
            MemberProfileEditCopy.edit,
            MemberProfileEditCopy.cancel,
            MemberProfileEditCopy.save,
            MemberProfileEditCopy.saving,
            MemberProfileEditCopy.firstName,
            MemberProfileEditCopy.lastName,
            MemberProfileEditCopy.phone,
            MemberProfileEditCopy.email,
            MemberProfileEditCopy.firstNameRequired,
            MemberProfileEditCopy.saved,
            MemberProfileEditCopy.error,
        ]
        XCTAssertEqual(MemberProfileEditCopy.edit, "edit")
        XCTAssertEqual(MemberProfileEditCopy.cancel, "cancel")
        XCTAssertEqual(MemberProfileEditCopy.save, "save")
        XCTAssertEqual(MemberProfileEditCopy.saving, "saving…")
        XCTAssertEqual(MemberProfileEditCopy.firstName, "first name")
        XCTAssertEqual(MemberProfileEditCopy.lastName, "last name (optional)")
        XCTAssertEqual(MemberProfileEditCopy.phone, "phone number")
        XCTAssertEqual(MemberProfileEditCopy.email, "email")
        XCTAssertEqual(MemberProfileEditCopy.firstNameRequired, "first name required")
        XCTAssertEqual(MemberProfileEditCopy.saved, "member updated ✓")
        XCTAssertEqual(MemberProfileEditCopy.error, "couldn't save changes — try again")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func profileMemberJSON() -> [String: Any] {
        var row = adminMemberJSON(id: "u-2", name: "Ada Lovelace", phone: "+15555550100", email: "ada@pda.test", bio: "")
        row["first_name"] = "ada"
        row["last_name"] = "lovelace"
        return row
    }

    func test_memberRoleLocked_onlyDefaultAdminForNonAdmin() {
        let admin = AdminRole(id: "r-admin", name: "admin", permissions: [], userCount: 1, isDefault: true)
        let member = AdminRole(id: "r-member", name: "member", permissions: [], userCount: 1, isDefault: true)
        let vetter = AdminRole(id: "r-vetter", name: "vetter", permissions: [], userCount: 1)
        let namedAdmin = AdminRole(id: "r-fake", name: "admin", permissions: [], userCount: 0)
        XCTAssertTrue(memberRoleLocked(admin, viewerIsAdmin: false))
        XCTAssertFalse(memberRoleLocked(admin, viewerIsAdmin: true))
        XCTAssertFalse(memberRoleLocked(member, viewerIsAdmin: false))
        XCTAssertFalse(memberRoleLocked(vetter, viewerIsAdmin: false))
        XCTAssertFalse(memberRoleLocked(namedAdmin, viewerIsAdmin: false))
    }

    func test_saveMemberRoles_patchesRoleIDs() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            let path = routePath(request.url)
            if request.httpMethod == "GET", path == "/api/auth/roles/" {
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                return MockHTTP.json(200, [
                    roleJSON(id: "r-member", name: "member", isDefault: true),
                    roleJSON(id: "r-vetter", name: "vetter", isDefault: false),
                    roleJSON(id: "r-admin", name: "admin", isDefault: true),
                ])
            }
            if request.httpMethod == "PATCH" {
                XCTAssertEqual(path, "/api/auth/users/u-2/roles/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                let patch = try JSONDecoder().decode(MemberRolesPatchBody.self, from: request.httpBody ?? Data())
                XCTAssertEqual(Set(patch.role_ids), Set(["r-member", "r-vetter"]))
                return MockHTTP.json(200, self.roleMemberJSON(roleIDs: ["r-member", "r-vetter"]))
            }
            return MockHTTP.json(200, [self.roleMemberJSON(roleIDs: ["r-member"])])
        }
        let model = AdminMemberDetailModel(client: makeClient(tokens))
        await model.load(id: "u-2")
        await model.loadRoles()
        XCTAssertEqual(model.selectedRoleIDs, Set(["r-member"]))
        XCTAssertEqual(model.roleCatalog.map(\.name), ["member", "vetter", "admin"])
        model.toggleRole(
            AdminRole(id: "r-vetter", name: "vetter", permissions: [], userCount: 1),
            viewerIsAdmin: false
        )
        model.toggleRole(
            AdminRole(id: "r-admin", name: "admin", permissions: [], userCount: 1, isDefault: true),
            viewerIsAdmin: false
        )
        XCTAssertFalse(model.selectedRoleIDs.contains("r-admin"))
        await model.saveRoles()
        XCTAssertEqual(Set(model.member?.roles.map(\.id) ?? []), Set(["r-member", "r-vetter"]))
        XCTAssertEqual(model.toast, MemberRolesCopy.saved)
        XCTAssertNil(model.rolesError)
    }

    func test_saveMemberRoles_403WithoutManageUsers() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "GET", routePath(request.url) == "/api/auth/roles/" {
                return MockHTTP.json(200, [
                    roleJSON(id: "r-member", name: "member", isDefault: true),
                    roleJSON(id: "r-vetter", name: "vetter", isDefault: false),
                ])
            }
            if request.httpMethod == "PATCH" {
                return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "update_user_roles"]]])
            }
            return MockHTTP.json(200, [self.roleMemberJSON(roleIDs: ["r-member"])])
        }
        let model = AdminMemberDetailModel(client: makeClient(tokens))
        await model.load(id: "u-2")
        await model.loadRoles()
        model.toggleRole(
            AdminRole(id: "r-vetter", name: "vetter", permissions: [], userCount: 1),
            viewerIsAdmin: false
        )
        await model.saveRoles()
        XCTAssertEqual(Set(model.member?.roles.map(\.id) ?? []), Set(["r-member"]))
        XCTAssertEqual(model.rolesError, "couldn't save changes — try again")
        XCTAssertNil(model.toast)
    }

    func test_saveMemberRoles_skipsUnchanged() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTFail("unchanged roles must not patch")
                return MockHTTP.json(500, [:])
            }
            if request.httpMethod == "GET", routePath(request.url) == "/api/auth/roles/" {
                return MockHTTP.json(200, [roleJSON(id: "r-member", name: "member", isDefault: true)])
            }
            return MockHTTP.json(200, [self.roleMemberJSON(roleIDs: ["r-member"])])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        await model.loadRoles()
        XCTAssertTrue(model.rolesUnchanged)
        await model.saveRoles()
        XCTAssertNil(model.toast)
        XCTAssertNil(model.rolesError)
    }

    func test_loadMemberRoles_hidesCatalogOnFailure() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "GET", routePath(request.url) == "/api/auth/roles/" {
                return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
            }
            return MockHTTP.json(200, [self.roleMemberJSON(roleIDs: ["r-member"])])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-2")
        await model.loadRoles()
        XCTAssertTrue(model.rolesUnavailable)
        XCTAssertTrue(model.roleCatalog.isEmpty)
        XCTAssertNil(model.rolesError)
    }

    func test_memberRolesCopy_isLowercase() {
        let blobs = [
            MemberRolesCopy.title,
            MemberRolesCopy.loading,
            MemberRolesCopy.save,
            MemberRolesCopy.saving,
            MemberRolesCopy.saved,
            MemberRolesCopy.error,
        ]
        XCTAssertEqual(MemberRolesCopy.title, "roles")
        XCTAssertEqual(MemberRolesCopy.loading, "loading roles…")
        XCTAssertEqual(MemberRolesCopy.save, "save roles")
        XCTAssertEqual(MemberRolesCopy.saving, "saving…")
        XCTAssertEqual(MemberRolesCopy.saved, "roles updated ✓")
        XCTAssertEqual(MemberRolesCopy.error, "couldn't save changes — try again")
        XCTAssertEqual(
            memberRolesURL(base: base, id: "u-2").absoluteString,
            "https://pda.test/api/auth/users/u-2/roles/"
        )
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func roleMemberJSON(roleIDs: [String]) -> [String: Any] {
        var row = adminMemberJSON(id: "u-2", name: "Ada Lovelace", phone: "+15555550100", email: "ada@pda.test", bio: "")
        row["roles"] = roleIDs.map { id -> [String: Any] in
            [
                "id": id,
                "name": id == "r-admin" ? "admin" : (id == "r-vetter" ? "vetter" : "member"),
                "is_default": id != "r-vetter",
                "permissions": [] as [String],
            ]
        }
        return row
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

private struct MemberProfilePatchBody: Decodable {
    let first_name: String?
    let last_name: String?
    let phone_number: String?
    let email: String?
    let is_paused: Bool?
    let has_joined_whatsapp: Bool?
}

private func roleJSON(id: String, name: String, isDefault: Bool) -> [String: Any] {
    [
        "id": id,
        "name": name,
        "is_default": isDefault,
        "permissions": [],
        "user_count": 1,
    ]
}

private struct MemberRolesPatchBody: Decodable {
    let role_ids: [String]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
