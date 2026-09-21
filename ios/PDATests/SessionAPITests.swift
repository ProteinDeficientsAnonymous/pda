import Foundation
import XCTest

@testable import PDA

final class SessionAPITests: XCTestCase {
    private let base = URL(string: "https://pda.test")!
    private var tokens: MemoryTokenStore!

    override func setUp() {
        super.setUp()
        tokens = MemoryTokenStore()
        MockHTTP.handler = nil
    }

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_checkPhone_postsPhoneNumber_andMapsStatuses() async throws {
        let seen = RequestLog()
        MockHTTP.handler = { request in
            seen.append(request)
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/check-phone/")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["phone_number"] as? String, "+15555550100")
            XCTAssertNil(body["refresh"])
            return MockHTTP.json(200, ["status": seen.count == 1 ? "member" : seen.count == 2 ? "pending" : "unknown"])
        }
        let client = makeClient()
        let member = try await client.checkPhone("+15555550100")
        let pending = try await client.checkPhone("+15555550100")
        let unknown = try await client.checkPhone("+15555550100")
        XCTAssertEqual(member, .member)
        XCTAssertEqual(pending, .pending)
        XCTAssertEqual(unknown, .unknown)
        XCTAssertEqual(seen.count, 3)
    }

    func test_login_storesAccessJWTInTokenStore() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/auth/login/")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["phone_number"] as? String, "+15555550100")
            XCTAssertEqual(body["password"] as? String, "secret")
            XCTAssertNil(body["refresh"])
            return MockHTTP.json(
                200,
                ["access": "access-jwt"],
                headers: ["Set-Cookie": "refresh_token=rt-cookie; Path=/; HttpOnly; SameSite=Lax"]
            )
        }
        let client = makeClient()
        try await client.login(phone: "+15555550100", password: "secret")
        XCTAssertEqual(try tokens.load(), "access-jwt")
    }

    func test_authorizedGET_on401_postsCookieRefreshWithoutJSONRefresh() async throws {
        var calls: [URLRequest] = []
        MockHTTP.handler = { request in
            calls.append(request)
            let path = routePath(request.url)
            if path == "/api/auth/me/", calls.filter({ routePath($0.url) == "/api/auth/me/" }).count == 1 {
                return MockHTTP.json(401, ["detail": [["code": "auth.token_invalid"]]])
            }
            if path == "/api/auth/refresh/" {
                XCTAssertEqual(request.httpMethod, "POST")
                XCTAssertNil(request.json?["refresh"])
                let raw = request.httpBody.flatMap { String(data: $0, encoding: .utf8) } ?? ""
                XCTAssertFalse(raw.contains("refresh"), "do not send a JSON refresh token")
                return MockHTTP.json(200, ["access": "access-v2"])
            }
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-v2")
            return MockHTTP.json(200, Self.mePayload)
        }
        try tokens.save("access-v1")
        let user = try await makeClient().me()
        XCTAssertEqual(user.id, "user-1")
        XCTAssertEqual(try tokens.load(), "access-v2")
        XCTAssertEqual(calls.map { routePath($0.url) }, [
            "/api/auth/me/",
            "/api/auth/refresh/",
            "/api/auth/me/",
        ])
    }

    func test_loginCopy_isLowercaseAndHasNoJoinScreen() {
        XCTAssertEqual(LoginCopy.welcomeTitle, "welcome back")
        XCTAssertEqual(LoginCopy.welcomeSubtitle, "sign in to your pda account")
        XCTAssertEqual(LoginCopy.phoneLabel, "phone number")
        XCTAssertEqual(LoginCopy.passwordLabel, "password")
        XCTAssertEqual(LoginCopy.continueButton, "continue")
        XCTAssertEqual(LoginCopy.signInButton, "sign in")
        XCTAssertEqual(LoginCopy.pendingTitle, "under review")
        XCTAssertEqual(LoginCopy.unknownTitle, "no account for that number")
        let blobs = [
            LoginCopy.welcomeTitle,
            LoginCopy.welcomeSubtitle,
            LoginCopy.phoneLabel,
            LoginCopy.passwordLabel,
            LoginCopy.continueButton,
            LoginCopy.signInButton,
            LoginCopy.pendingTitle,
            LoginCopy.pendingBody,
            LoginCopy.unknownTitle,
            LoginCopy.unknownBody,
            LoginCopy.backButton,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_loginModel_routesPhoneStatusesWithoutJoin() async {
        let client = makeClient()
        MockHTTP.handler = { request in
            let body = try XCTUnwrap(request.json)
            let phone = body["phone_number"] as? String
            let status: String = switch phone {
            case "+15555550100": "member"
            case "+15555550101": "pending"
            default: "unknown"
            }
            return MockHTTP.json(200, ["status": status])
        }

        let member = LoginModel(client: client)
        member.phone = "+15555550100"
        await member.submitPhone()
        XCTAssertEqual(member.step, .password)

        let pending = LoginModel(client: client)
        pending.phone = "+15555550101"
        await pending.submitPhone()
        XCTAssertEqual(pending.step, .pending)

        let unknown = LoginModel(client: client)
        unknown.phone = "+15555550999"
        await unknown.submitPhone()
        XCTAssertEqual(unknown.step, .unknown)
        XCTAssertFalse(unknown.unknownBody.contains("join"))
    }

    func test_login_mapsArchivedAndPausedCodes() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "auth.account_archived", "field": NSNull()]]])
        }
        do {
            try await makeClient().login(phone: "+15555550100", password: "x")
            XCTFail("archived login should throw")
        } catch let error as SessionError {
            XCTAssertEqual(error.code, "auth.account_archived")
            XCTAssertEqual(error.message, "this account is no longer active")
        } catch {
            XCTFail("wrong error \(error)")
        }

        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "auth.account_paused"]]])
        }
        do {
            try await makeClient().login(phone: "+15555550100", password: "x")
            XCTFail("paused login should throw")
        } catch let error as SessionError {
            XCTAssertEqual(error.code, "auth.account_paused")
            XCTAssertEqual(error.message, "your membership is currently paused")
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_me_mapsPausedWithoutRefreshing() async throws {
        try tokens.save("access-v1")
        var paths: [String] = []
        MockHTTP.handler = { request in
            paths.append(routePath(request.url))
            return MockHTTP.json(403, ["detail": [["code": "auth.account_paused"]]])
        }
        do {
            _ = try await makeClient().me()
            XCTFail("paused me should throw")
        } catch let error as SessionError {
            XCTAssertEqual(error.code, "auth.account_paused")
            XCTAssertEqual(error.message, "your membership is currently paused")
        } catch {
            XCTFail("wrong error \(error)")
        }
        XCTAssertEqual(paths, ["/api/auth/me/"])
        XCTAssertEqual(try tokens.load(), "access-v1")
    }

    func test_loginModel_surfacesArchivedCopy() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "auth.account_archived"]]])
        }
        let model = LoginModel(client: makeClient())
        model.phone = "+15555550100"
        model.password = "secret"
        await model.signIn()
        XCTAssertEqual(model.error, "this account is no longer active")
        XCTAssertNil(try tokens.load())
    }

    func test_logout_postsLogoutAndClearsAccessToken() async throws {
        try tokens.save("access-jwt")
        var method: String?
        MockHTTP.handler = { request in
            XCTAssertEqual(routePath(request.url), "/api/auth/logout/")
            method = request.httpMethod
            XCTAssertNil(request.json?["refresh"])
            return MockHTTP.json(
                200,
                ["detail": "logged out"],
                headers: ["Set-Cookie": "refresh_token=; Path=/; Max-Age=0"]
            )
        }
        try await makeClient().logout()
        XCTAssertEqual(method, "POST")
        XCTAssertNil(try tokens.load())
    }

    func test_authSession_logoutClearsUser() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { _ in MockHTTP.json(200, ["detail": "logged out"]) }
        let session = AuthSession(client: makeClient())
        session.signedIn(
            try JSONDecoder().decode(
                SessionUser.self,
                from: try JSONSerialization.data(withJSONObject: Self.mePayload)
            )
        )
        XCTAssertNotNil(session.user)
        await session.logout()
        XCTAssertNil(session.user)
        XCTAssertNil(try tokens.load())
    }

    func test_keychainTokenStore_savesAndClearsAccessJWT() throws {
        let store = KeychainTokenStore(service: "anonymous.pda.ios.tests", account: "access")
        try store.clear()
        XCTAssertNil(try store.load())
        try store.save("jwt-from-keychain")
        XCTAssertEqual(try store.load(), "jwt-from-keychain")
        try store.clear()
        XCTAssertNil(try store.load())
    }

    func test_authGate_isNilWhenReadyOrLoggedOut() throws {
        XCTAssertNil(authGate(for: nil))
        XCTAssertNil(authGate(for: try user()))
    }

    func test_authGate_newPasswordWhenSetupPendingAndNameAndEmailOnFile() throws {
        XCTAssertEqual(
            authGate(for: try user(firstName: "ada", email: "a@b.c", needsPasswordReset: true)),
            .newPassword
        )
        XCTAssertEqual(
            authGate(for: try user(firstName: "ada", email: "a@b.c", needsOnboarding: true)),
            .newPassword
        )
    }

    func test_authGate_onboardingWhenNameOrEmailMissing() throws {
        XCTAssertEqual(
            authGate(for: try user(firstName: "", email: "a@b.c", needsOnboarding: true)),
            .onboarding
        )
        XCTAssertEqual(
            authGate(for: try user(firstName: "ada", email: "", needsOnboarding: true)),
            .onboarding
        )
    }

    func test_authGate_passwordSetupBeforeConsent() throws {
        XCTAssertEqual(
            authGate(for: try user(firstName: "", needsOnboarding: true, needsGuidelinesConsent: true)),
            .onboarding
        )
        XCTAssertEqual(
            authGate(for: try user(
                firstName: "ada",
                email: "a@b.c",
                needsPasswordReset: true,
                needsGuidelinesConsent: true
            )),
            .newPassword
        )
    }

    func test_authGate_consentBeforeEmail() throws {
        XCTAssertEqual(authGate(for: try user(needsGuidelinesConsent: true)), .consent)
        XCTAssertEqual(authGate(for: try user(needsSmsConsent: true)), .consent)
        XCTAssertEqual(authGate(for: try user(needsContactPrivacyConsent: true)), .consent)
        XCTAssertEqual(authGate(for: try user(email: "")), .email)
    }

    func test_gateCopy_isLowercaseAndHasNoJoin() {
        let blobs = [
            GateCopy.newPasswordTitle,
            GateCopy.onboardingTitle,
            GateCopy.consentTitle,
            GateCopy.emailTitle,
            GateCopy.emailBody,
            GateCopy.notNow,
            GateCopy.savePassword,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_directoryChrome_tentativeExplainsWithoutLoginBounce() throws {
        XCTAssertEqual(directoryChrome(for: nil), .login)
        XCTAssertEqual(directoryChrome(for: try user()), .open)
        let tentative = try user(isMember: false)
        XCTAssertEqual(
            directoryChrome(for: tentative),
            .locked(title: MemberLockCopy.directoryTitle, body: MemberLockCopy.directoryBody)
        )
        if case .login = directoryChrome(for: tentative) {
            XCTFail("tentative directory must explain, not bounce to login")
        }
    }

    func test_addEventChrome_tentativeExplainsWithoutLoginBounce() throws {
        XCTAssertEqual(addEventChrome(for: nil), .login)
        XCTAssertEqual(addEventChrome(for: try user()), .open)
        let tentative = try user(isMember: false)
        XCTAssertEqual(
            addEventChrome(for: tentative),
            .locked(title: MemberLockCopy.addEventTitle, body: MemberLockCopy.addEventBody)
        )
        if case .login = addEventChrome(for: tentative) {
            XCTFail("tentative add-event must explain, not bounce to login")
        }
        XCTAssertNotEqual(addEventChrome(for: try user(isMember: false)), .open)
    }

    func test_allowedEventTypes_officialAndClubRequirePerms() throws {
        XCTAssertEqual(allowedEventTypes(for: try user()), ["community"])
        XCTAssertEqual(
            allowedEventTypes(for: try user(permissions: ["tag_official_event"])),
            ["community", "official"]
        )
        XCTAssertEqual(
            allowedEventTypes(for: try user(permissions: ["tag_club_event"])),
            ["community", "club"]
        )
        XCTAssertEqual(
            allowedEventTypes(for: try user(permissions: ["tag_official_event", "tag_club_event"])),
            ["community", "official", "club"]
        )
        XCTAssertEqual(allowedEventTypes(for: try user(isMember: false, permissions: ["tag_official_event"])), [])
    }

    func test_addEventCopy_isLowercaseAndHasNoJoin() {
        let blobs = [
            AddEventCopy.title,
            AddEventCopy.titleLabel,
            AddEventCopy.whenLabel,
            AddEventCopy.descriptionLabel,
            AddEventCopy.save,
            AddEventCopy.typeCommunity,
            AddEventCopy.typeOfficial,
            AddEventCopy.typeClub,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_createEvent_postsTitleTimeDescriptionWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/events/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["title"] as? String, "potluck")
            XCTAssertEqual(body["description"] as? String, "bring a dish")
            XCTAssertEqual(body["start_datetime"] as? String, "2026-10-01T18:00:00Z")
            XCTAssertEqual(body["event_type"] as? String, "community")
            return MockHTTP.json(201, ["id": "evt-new", "title": "potluck", "event_type": "community"])
        }
        let created = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).create(title: "potluck", start: "2026-10-01T18:00:00Z", description: "bring a dish", eventType: "community")
        XCTAssertEqual(created.id, "evt-new")
        XCTAssertEqual(created.title, "potluck")
    }

    func test_canEditEvent_memberHostOnly() throws {
        let hosted = try Event.decodeJSON(#"{ "id": "e", "title": "e", "co_host_ids": ["user-1"] }"#)
        let other = try Event.decodeJSON(#"{ "id": "o", "title": "o", "co_host_ids": ["user-2"] }"#)
        let member = try user()
        let tentative = try user(isMember: false)
        XCTAssertTrue(canEditEvent(hosted, user: member))
        XCTAssertFalse(canEditEvent(hosted, user: tentative))
        XCTAssertFalse(canEditEvent(hosted, user: nil))
        XCTAssertFalse(canEditEvent(other, user: member))
    }

    func test_editEventCopy_isLowercaseAndHasNoJoin() {
        let blobs = [EditEventCopy.title, EditEventCopy.save]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_updateEvent_patchesTitleTimeDescriptionWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["title"] as? String, "potluck v2")
            XCTAssertEqual(body["description"] as? String, "bring two dishes")
            XCTAssertEqual(body["start_datetime"] as? String, "2026-10-02T18:00:00Z")
            XCTAssertNil(body["event_type"])
            return MockHTTP.json(200, ["id": "evt-1", "title": "potluck v2"])
        }
        let updated = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).update(id: "evt-1", title: "potluck v2", start: "2026-10-02T18:00:00Z", description: "bring two dishes")
        XCTAssertEqual(updated.id, "evt-1")
        XCTAssertEqual(updated.title, "potluck v2")
    }

    func test_canShowEventComments_signedInOrGuestTokenWhenRsvpEnabled() throws {
        let open = try Event.decodeJSON(#"{ "id": "e", "title": "e", "rsvp_enabled": true }"#)
        let closed = try Event.decodeJSON(#"{ "id": "c", "title": "c", "rsvp_enabled": false }"#)
        XCTAssertTrue(canShowEventComments(open, signedIn: true, hasGuestToken: false))
        XCTAssertTrue(canShowEventComments(open, signedIn: false, hasGuestToken: true))
        XCTAssertFalse(canShowEventComments(open, signedIn: false, hasGuestToken: false))
        XCTAssertFalse(canShowEventComments(closed, signedIn: true, hasGuestToken: true))
    }

    func test_commentPrompt_rsvpRequiredVsLoginRequired() {
        XCTAssertNil(commentComposerPrompt(canPost: true, reason: nil))
        XCTAssertEqual(
            commentComposerPrompt(canPost: false, reason: "rsvp_required"),
            EventCommentCopy.rsvpRequired
        )
        XCTAssertEqual(
            commentComposerPrompt(canPost: false, reason: "login_required"),
            EventCommentCopy.loginRequired
        )
        XCTAssertEqual(
            commentComposerPrompt(canPost: false, reason: nil),
            EventCommentCopy.loginRequired
        )
    }

    func test_visibleComments_hiddenWhenCannotPost() throws {
        let hidden = try EventCommentList.decodeJSON("""
        {"can_post":false,"cannot_post_reason":"rsvp_required","items":[{"id":"c1","author_display_name":"ada","body":"leaked"}]}
        """)
        let shown = try EventCommentList.decodeJSON("""
        {"can_post":true,"items":[{"id":"c1","author_display_name":"ada","body":"visible"}]}
        """)
        XCTAssertEqual(visibleComments(hidden).map(\.body), [])
        XCTAssertEqual(visibleComments(shown).map(\.body), ["visible"])
    }

    func test_eventCommentCopy_isLowercase() {
        let blobs = [
            EventCommentCopy.title,
            EventCommentCopy.post,
            EventCommentCopy.placeholder,
            EventCommentCopy.rsvpRequired,
            EventCommentCopy.loginRequired,
            EventCommentCopy.loadError,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_listComments_getsWithBearerAndDecodesCanPost() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/comments/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            XCTAssertNil(request.url?.query)
            return MockHTTP.json(200, [
                "can_post": true,
                "cannot_post_reason": NSNull(),
                "items": [[
                    "id": "c1",
                    "author_display_name": "ada",
                    "body": "bringing snacks",
                    "is_deleted": false,
                    "reactions": [["emoji": "❤️", "count": 2, "reacted_by_me": true]],
                ]],
            ])
        }
        let list = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).comments(eventId: "evt-1")
        XCTAssertTrue(list.canPost)
        XCTAssertEqual(list.items.first?.body, "bringing snacks")
        XCTAssertEqual(list.items.first?.reactions.first?.emoji, "❤️")
        XCTAssertEqual(list.items.first?.reactions.first?.count, 2)
        XCTAssertEqual(list.items.first?.reactions.first?.reactedByMe, true)
    }

    func test_listComments_includesGuestTokenQueryWithoutBearer() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/comments/")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            XCTAssertEqual(request.url?.query, "token=rsvp-token")
            return MockHTTP.json(200, ["can_post": true, "items": []])
        }
        let list = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session()
        ).comments(eventId: "evt-1", guestToken: "rsvp-token")
        XCTAssertTrue(list.canPost)
    }

    func test_postComment_postsBodyWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/comments/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["body"] as? String, "bringing snacks")
            return MockHTTP.json(201, ["id": "c-new", "author_display_name": "ada", "body": "bringing snacks"])
        }
        let posted = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).postComment(eventId: "evt-1", body: "bringing snacks")
        XCTAssertEqual(posted.id, "c-new")
        XCTAssertEqual(posted.body, "bringing snacks")
    }

    func test_toggleReaction_postsEmojiWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(
                routePath(request.url),
                "/api/community/events/evt-1/comments/c1/reactions/"
            )
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["emoji"] as? String, "❤️")
            return MockHTTP.json(200, [
                "id": "c1",
                "author_display_name": "ada",
                "body": "bringing snacks",
                "reactions": [["emoji": "❤️", "count": 1, "reacted_by_me": true]],
            ])
        }
        let updated = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).toggleReaction(eventId: "evt-1", commentId: "c1", emoji: "❤️")
        XCTAssertEqual(updated.reactions.first?.reactedByMe, true)
        XCTAssertEqual(updated.reactions.first?.count, 1)
    }

    func test_canShowEventPoll_hasPollAndNotWon() throws {
        let none = try Event.decodeJSON(#"{ "id": "e", "title": "e" }"#)
        let open = try Event.decodeJSON(#"{ "id": "e", "title": "e", "has_poll": true }"#)
        XCTAssertFalse(canShowEventPoll(none, winningDatetime: nil))
        XCTAssertTrue(canShowEventPoll(open, winningDatetime: nil))
        XCTAssertFalse(canShowEventPoll(open, winningDatetime: Date()))
    }

    func test_pollVoteChrome_guestSignsInToVote() {
        XCTAssertEqual(pollVoteChrome(signedIn: false), .login)
        XCTAssertEqual(pollVoteChrome(signedIn: true), .vote)
    }

    func test_mergedPollVotes_setsChangesAndRetracts() {
        XCTAssertEqual(mergedPollVotes(current: [:], optionId: "a", choice: "yes"), ["a": "yes"])
        XCTAssertEqual(
            mergedPollVotes(current: ["a": "yes"], optionId: "a", choice: "maybe"),
            ["a": "maybe"]
        )
        XCTAssertEqual(mergedPollVotes(current: ["a": "yes"], optionId: "a", choice: "yes"), [:])
    }

    func test_sortPollOptionsByVotes_yesThenMaybeThenEarliest() throws {
        let poll = try EventPoll.decodeJSON("""
        {
          "id": "p1",
          "event_id": "evt-1",
          "is_active": true,
          "options": [
            {"id": "late", "datetime": "2026-05-02T18:00:00Z", "display_order": 0, "yes_count": 2, "maybe_count": 0, "no_count": 0},
            {"id": "more-maybe", "datetime": "2026-05-01T18:00:00Z", "display_order": 1, "yes_count": 2, "maybe_count": 3, "no_count": 0},
            {"id": "most-yes", "datetime": "2026-05-03T18:00:00Z", "display_order": 2, "yes_count": 5, "maybe_count": 0, "no_count": 0}
          ]
        }
        """)
        XCTAssertEqual(sortPollOptionsByVotes(poll.options).map(\.id), ["most-yes", "more-maybe", "late"])
    }

    func test_eventPollCopy_isLowercaseAndHasNoJoin() {
        let blobs = [
            EventPollCopy.title,
            EventPollCopy.respond,
            EventPollCopy.signIn,
            EventPollCopy.yes,
            EventPollCopy.maybe,
            EventPollCopy.no,
            EventPollCopy.loadError,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_getPoll_getsWithBearerAndDecodesOptions() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/poll/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "id": "p1",
                "event_id": "evt-1",
                "is_active": true,
                "options": [[
                    "id": "opt-a",
                    "datetime": "2026-05-01T18:00:00Z",
                    "yes_count": 2,
                    "maybe_count": 1,
                    "no_count": 0,
                ]],
                "my_votes": ["opt-a": "yes"],
            ])
        }
        let poll = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).poll(eventId: "evt-1")
        XCTAssertEqual(poll.id, "p1")
        XCTAssertEqual(poll.options.first?.yesCount, 2)
        XCTAssertEqual(poll.myVotes["opt-a"], "yes")
    }

    func test_votePoll_postsVotesMapWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/poll/vote/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try XCTUnwrap(request.json)
            let votes = try XCTUnwrap(body["votes"] as? [String: Any])
            XCTAssertEqual(votes["opt-a"] as? String, "yes")
            return MockHTTP.json(200, [
                "id": "p1",
                "event_id": "evt-1",
                "is_active": true,
                "options": [],
                "my_votes": ["opt-a": "yes"],
            ])
        }
        let poll = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).votePoll(eventId: "evt-1", votes: ["opt-a": "yes"])
        XCTAssertEqual(poll.myVotes["opt-a"], "yes")
    }

    func test_canShowCohostInvite_pendingAndNotPast() throws {
        let none = try Event.decodeJSON(#"{ "id": "e", "title": "e" }"#)
        let pending = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "my_pending_cohost_invite_id": "inv1" }"#
        )
        let past = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "my_pending_cohost_invite_id": "inv1", "is_past": true }"#
        )
        XCTAssertFalse(canShowCohostInvite(none))
        XCTAssertTrue(canShowCohostInvite(pending))
        XCTAssertFalse(canShowCohostInvite(past))
    }

    func test_cohostInviteMessage_usesCreatorNameOrSomeone() {
        XCTAssertEqual(cohostInviteMessage(createdByName: "Alice"), "alice invited you to co-host")
        XCTAssertEqual(cohostInviteMessage(createdByName: ""), "someone invited you to co-host")
    }

    func test_cohostInviteCopy_isLowercaseAndHasNoJoin() {
        let blobs = [CohostInviteCopy.accept, CohostInviteCopy.decline]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_acceptCohostInvite_postsWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(
                routePath(request.url),
                "/api/community/events/evt-1/cohost-invites/inv1/accept/"
            )
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, ["id": "evt-1", "title": "potluck", "co_host_ids": ["user-1"]])
        }
        let event = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).acceptCohostInvite(eventId: "evt-1", inviteId: "inv1")
        XCTAssertEqual(event.id, "evt-1")
        XCTAssertTrue(event.coHostIds.contains("user-1"))
        XCTAssertNil(event.myPendingCohostInviteId)
    }

    func test_declineCohostInvite_postsWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(
                routePath(request.url),
                "/api/community/events/evt-1/cohost-invites/inv1/decline/"
            )
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, ["id": "evt-1", "title": "potluck"])
        }
        let event = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).declineCohostInvite(eventId: "evt-1", inviteId: "inv1")
        XCTAssertEqual(event.id, "evt-1")
        XCTAssertNil(event.myPendingCohostInviteId)
    }

    func test_canInviteGuests_hostManagerOrRsvpdWhenAllMembers() throws {
        let host = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "rsvp_enabled": true, "co_host_ids": ["user-1"] }"#
        )
        let rsvpd = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "rsvp_enabled": true, "invite_permission": "all_members", "my_rsvp": "attending" }"#
        )
        let maybe = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "rsvp_enabled": true, "invite_permission": "all_members", "my_rsvp": "maybe" }"#
        )
        let closed = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "rsvp_enabled": true, "invite_permission": "co_hosts_only", "my_rsvp": "attending" }"#
        )
        let noRsvp = try Event.decodeJSON(#"{ "id": "e", "title": "e", "rsvp_enabled": true, "invite_permission": "all_members" }"#)
        let past = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "rsvp_enabled": true, "co_host_ids": ["user-1"], "is_past": true }"#
        )
        let cancelled = try Event.decodeJSON(
            #"{ "id": "e", "title": "e", "rsvp_enabled": true, "co_host_ids": ["user-1"], "status": "cancelled" }"#
        )
        let rsvpOff = try Event.decodeJSON(#"{ "id": "e", "title": "e", "co_host_ids": ["user-1"] }"#)
        let member = try user()
        let manager = try user(permissions: ["manage_events"])
        XCTAssertTrue(canInviteGuests(host, user: member))
        XCTAssertTrue(canInviteGuests(rsvpd, user: member))
        XCTAssertTrue(canInviteGuests(maybe, user: member))
        XCTAssertTrue(canInviteGuests(noRsvp, user: manager))
        XCTAssertFalse(canInviteGuests(closed, user: member))
        XCTAssertFalse(canInviteGuests(noRsvp, user: member))
        XCTAssertFalse(canInviteGuests(past, user: member))
        XCTAssertFalse(canInviteGuests(cancelled, user: member))
        XCTAssertFalse(canInviteGuests(rsvpOff, user: member))
        XCTAssertFalse(canInviteGuests(host, user: nil))
    }

    func test_inviteCopy_isLowercaseAndHasNoJoin() {
        let blobs = [InviteCopy.title, InviteCopy.search, InviteCopy.send, InviteCopy.cancel]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_searchMembers_getsQueryWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/search/")
            XCTAssertEqual(request.url?.query, "q=ada")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [["id": "u-2", "full_name": "Ada Lovelace", "phone_number": "+1555"]])
        }
        let found = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).searchMembers(query: "ada")
        XCTAssertEqual(found.first?.id, "u-2")
        XCTAssertEqual(found.first?.name, "Ada Lovelace")
    }

    func test_inviteGuests_postsUserIdsWithBearer() async throws {
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/invitations/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["user_ids"] as? [String], ["u-2"])
            return MockHTTP.json(200, ["id": "evt-1", "title": "potluck", "invited_user_ids": ["u-2"]])
        }
        let event = try await EventsClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: tokens
        ).inviteGuests(eventId: "evt-1", userIds: ["u-2"])
        XCTAssertEqual(event.id, "evt-1")
        XCTAssertEqual(event.invitedUserIds, ["u-2"])
    }

    func test_memberLockCopy_isLowercaseAndHasNoJoin() {
        let blobs = [
            MemberLockCopy.directoryTitle,
            MemberLockCopy.directoryBody,
            MemberLockCopy.addEventTitle,
            MemberLockCopy.addEventBody,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
            XCTAssertFalse(text.contains("sign in"), text)
        }
    }

    func test_canSeeMemberEventDetails_tentativeOnlyOfficialAndClub() throws {
        let tentative = try user(isMember: false)
        let member = try user()
        let official = try Event.decodeJSON(#"{ "id": "o", "title": "o", "event_type": "official" }"#)
        let club = try Event.decodeJSON(#"{ "id": "c", "title": "c", "event_type": "club" }"#)
        let community = try Event.decodeJSON(#"{ "id": "m", "title": "m", "event_type": "community" }"#)

        XCTAssertFalse(canSeeMemberEventDetails(nil, event: official))
        XCTAssertFalse(canSeeMemberEventDetails(tentative, event: community))
        XCTAssertTrue(canSeeMemberEventDetails(tentative, event: official))
        XCTAssertTrue(canSeeMemberEventDetails(tentative, event: club))
        XCTAssertTrue(canSeeMemberEventDetails(member, event: community))
        XCTAssertTrue(canSeeMemberEventDetails(member, event: official))
    }

    func test_myRsvpsDestination_authedGoesToMyEvents() throws {
        XCTAssertEqual(myRsvpsDestination(user: nil, hasGuestToken: false), .login)
        XCTAssertEqual(myRsvpsDestination(user: nil, hasGuestToken: true), .guestRsvps)
        XCTAssertEqual(myRsvpsDestination(user: try user(), hasGuestToken: true), .myEvents)
        XCTAssertEqual(myRsvpsDestination(user: try user(), hasGuestToken: false), .myEvents)
    }

    func test_publicRsvpCopy_isLowercaseAndHasNoJoin() {
        let blobs = [
            PublicRsvpCopy.title,
            PublicRsvpCopy.phoneLabel,
            PublicRsvpCopy.firstNameLabel,
            PublicRsvpCopy.emailLabel,
            PublicRsvpCopy.going,
            PublicRsvpCopy.maybe,
            PublicRsvpCopy.submit,
            PublicRsvpCopy.memberBody,
            PublicRsvpCopy.myRsvpsTitle,
            PublicRsvpCopy.empty,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
            XCTAssertFalse(text.contains("join"), text)
        }
    }

    func test_publicRsvpCheckPhone_postsEventScopedPhone() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/public/events/evt-1/rsvp-phone-check/")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["phone_number"] as? String, "+15555550999")
            return MockHTTP.json(200, ["status": "new"])
        }
        let status = try await PublicRsvpClient(baseURL: base, session: MockHTTP.session())
            .checkPhone(eventId: "evt-1", phone: "+15555550999")
        XCTAssertEqual(status, .new)
    }

    func test_publicRsvpSubmit_storesToken() async throws {
        let tokens = RsvpTokenStore(defaults: UserDefaults(suiteName: "pda-rsvp-test-\(UUID().uuidString)")!)
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/public/events/evt-1/rsvp/")
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["phone_number"] as? String, "+15555550999")
            XCTAssertEqual(body["first_name"] as? String, "ada")
            XCTAssertEqual(body["email"] as? String, "ada@pda.test")
            XCTAssertEqual(body["status"] as? String, "attending")
            XCTAssertEqual(body["website"] as? String, "")
            return MockHTTP.json(200, [
                "rsvp_token": "tok-abc",
                "rsvp": ["status": "attending", "has_plus_one": false],
                "event": ["id": "evt-1", "title": "meetup"],
            ])
        }
        let token = try await PublicRsvpClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
            .submit(
                eventId: "evt-1",
                phone: "+15555550999",
                firstName: "ada",
                email: "ada@pda.test",
                status: "attending"
            )
        XCTAssertEqual(token, "tok-abc")
        XCTAssertEqual(tokens.load(), "tok-abc")
    }

    func test_myRsvps_sendsTokenQuery() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/public/my-rsvps/")
            XCTAssertEqual(request.url?.query, "token=tok-abc")
            return MockHTTP.json(200, [
                "user": ["display_name": "ada", "email": "ada@pda.test", "phone_number": "+15555550999"],
                "rsvps": [
                    [
                        "status": "attending",
                        "has_plus_one": false,
                        "event": ["id": "evt-1", "title": "meetup", "event_type": "official"],
                    ],
                ],
            ])
        }
        let items = try await PublicRsvpClient(baseURL: base, session: MockHTTP.session())
            .myRsvps(token: "tok-abc")
        XCTAssertEqual(items.map(\.title), ["meetup"])
        XCTAssertEqual(items.map(\.status), ["attending"])
    }

    func test_publicRsvpCheckPhone_mapsMemberWithoutJoin() async throws {
        MockHTTP.handler = { _ in MockHTTP.json(200, ["status": "member"]) }
        let status = try await PublicRsvpClient(baseURL: base, session: MockHTTP.session())
            .checkPhone(eventId: "evt-1", phone: "+15555550100")
        XCTAssertEqual(status, .member)
        XCTAssertFalse(PublicRsvpCopy.memberBody.contains("join"))
    }

    func test_eventCopy_tentativeCommunityLooksLoggedOut_officialDoesNot() throws {
        let tentative = try user(isMember: false)
        let member = try user()
        let community = try Event.decodeJSON(#"{ "id": "m", "title": "potluck", "event_type": "community" }"#)
        let official = try Event.decodeJSON(#"{ "id": "o", "title": "meetup", "event_type": "official" }"#)

        let guestCommunity = GuestEventCopy.make(community)
        let tentativeCommunity = GuestEventCopy.make(community, user: tentative)
        XCTAssertEqual(tentativeCommunity.moreHintTitle, guestCommunity.moreHintTitle)
        XCTAssertEqual(tentativeCommunity.moreHintBody, guestCommunity.moreHintBody)

        let tentativeOfficial = GuestEventCopy.make(official, user: tentative)
        XCTAssertEqual(tentativeOfficial.moreHintTitle, "")
        XCTAssertEqual(tentativeOfficial.moreHintBody, "")

        let memberCommunity = GuestEventCopy.make(community, user: member)
        XCTAssertEqual(memberCommunity.moreHintTitle, "")
        XCTAssertEqual(memberCommunity.moreHintBody, "")
    }

    private func user(
        firstName: String = "ada",
        email: String = "ada@pda.test",
        isMember: Bool = true,
        permissions: [String] = [],
        needsOnboarding: Bool = false,
        needsPasswordReset: Bool = false,
        needsGuidelinesConsent: Bool = false,
        needsSmsConsent: Bool = false,
        needsContactPrivacyConsent: Bool = false
    ) throws -> SessionUser {
        var payload = Self.mePayload
        payload["first_name"] = firstName
        payload["email"] = email
        payload["is_member"] = isMember
        payload["permissions"] = permissions
        payload["needs_onboarding"] = needsOnboarding
        payload["needs_password_reset"] = needsPasswordReset
        payload["needs_guidelines_consent"] = needsGuidelinesConsent
        payload["needs_sms_consent"] = needsSmsConsent
        payload["needs_contact_privacy_consent"] = needsContactPrivacyConsent
        return try JSONDecoder().decode(
            SessionUser.self,
            from: try JSONSerialization.data(withJSONObject: payload)
        )
    }

    private func makeClient() -> SessionClient {
        SessionClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}

extension SessionAPITests {
    static let mePayload: [String: Any] = [
        "id": "user-1",
        "phone_number": "+15555550100",
        "full_name": "seed member",
        "is_member": true,
        "is_paused": false,
        "date_joined": "2026-01-01T00:00:00Z",
        "roles": [],
    ]
}

private final class RequestLog: @unchecked Sendable {
    private let lock = NSLock()
    private var requests: [URLRequest] = []
    var count: Int {
        lock.lock()
        defer { lock.unlock() }
        return requests.count
    }

    func append(_ request: URLRequest) {
        lock.lock()
        requests.append(request)
        lock.unlock()
    }
}

enum MockHTTP {
    static let lock = NSLock()
    static var handler: ((URLRequest) throws -> (Int, Data, [String: String]))?

    static func session() -> URLSession {
        let config = URLSessionConfiguration.ephemeral
        config.protocolClasses = [MockURLProtocol.self]
        config.httpCookieAcceptPolicy = .always
        config.httpShouldSetCookies = true
        return URLSession(configuration: config)
    }

    static func json(_ status: Int, _ body: Any, headers: [String: String] = [:]) -> (Int, Data, [String: String]) {
        var next = headers
        next["Content-Type"] = "application/json"
        return (status, try! JSONSerialization.data(withJSONObject: body), next)
    }
}

final class MockURLProtocol: URLProtocol {
    override class func canInit(with request: URLRequest) -> Bool { true }
    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        var copy = request
        if copy.httpBody == nil, let stream = copy.httpBodyStream {
            stream.open()
            defer { stream.close() }
            var data = Data()
            let buf = UnsafeMutablePointer<UInt8>.allocate(capacity: 1024)
            defer { buf.deallocate() }
            while stream.hasBytesAvailable {
                let n = stream.read(buf, maxLength: 1024)
                if n <= 0 { break }
                data.append(buf, count: n)
            }
            copy.httpBody = data
        }
        return copy
    }

    override func startLoading() {
        var req = request
        if req.httpBody == nil, let stream = req.httpBodyStream {
            stream.open()
            defer { stream.close() }
            var body = Data()
            let buf = UnsafeMutablePointer<UInt8>.allocate(capacity: 1024)
            defer { buf.deallocate() }
            while stream.hasBytesAvailable {
                let n = stream.read(buf, maxLength: 1024)
                if n <= 0 { break }
                body.append(buf, count: n)
            }
            req.httpBody = body
        }
        MockHTTP.lock.lock()
        let handler = MockHTTP.handler
        MockHTTP.lock.unlock()
        do {
            let (status, data, headers) = try handler!(req)
            let response = HTTPURLResponse(
                url: req.url!,
                statusCode: status,
                httpVersion: "HTTP/1.1",
                headerFields: headers
            )!
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}

private extension URLRequest {
    var json: [String: Any]? {
        guard let httpBody, !httpBody.isEmpty else { return nil }
        return try? JSONSerialization.jsonObject(with: httpBody) as? [String: Any]
    }
}
