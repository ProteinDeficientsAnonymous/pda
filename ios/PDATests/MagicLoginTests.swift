import XCTest

@testable import PDA

final class MagicLoginTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_consumeMagicLogin_setsSessionAndReadyGate() async throws {
        let tokens = MemoryTokenStore()
        MockHTTP.handler = { request in
            let path = routePath(request.url)
            if path == "/api/auth/magic-login/tok/" {
                XCTAssertEqual(request.httpMethod, "GET")
                XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
                XCTAssertEqual(request.url?.absoluteString, "https://pda.test/api/auth/magic-login/tok/")
                return MockHTTP.json(200, ["access": "new-access"])
            }
            XCTAssertEqual(path, "/api/auth/me/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer new-access")
            return MockHTTP.json(200, self.meJSON())
        }
        let model = MagicConsumeModel(token: "tok", client: makeClient(tokens))
        let session = AuthSession(client: model.client)
        await model.consume()
        XCTAssertEqual(try tokens.load(), "new-access")
        XCTAssertEqual(model.state, .ready(nil))
        XCTAssertEqual(model.user?.id, "user-1")
        XCTAssertNil(authGate(for: model.user))
        XCTAssertTrue(model.apply(to: session))
        XCTAssertEqual(session.user?.id, "user-1")
    }

    func test_consumeMagicLogin_onboardingWhenNameMissing() async throws {
        let tokens = MemoryTokenStore()
        MockHTTP.handler = { request in
            if routePath(request.url) == "/api/auth/me/" {
                return MockHTTP.json(200, self.meJSON(firstName: "", email: "", needsOnboarding: true))
            }
            return MockHTTP.json(200, ["access": "new-access"])
        }
        let model = MagicConsumeModel(token: "tok", client: makeClient(tokens))
        await model.consume()
        XCTAssertEqual(model.state, .ready(.onboarding))
        XCTAssertEqual(authGate(for: model.user), .onboarding)
    }

    func test_consumeMagicLogin_newPasswordWhenNameAndEmailPresent() async throws {
        MockHTTP.handler = { request in
            if routePath(request.url) == "/api/auth/me/" {
                return MockHTTP.json(200, self.meJSON(needsPasswordReset: true))
            }
            return MockHTTP.json(200, ["access": "new-access"])
        }
        let model = MagicConsumeModel(token: "tok", client: makeClient())
        await model.consume()
        XCTAssertEqual(model.state, .ready(.newPassword))
    }

    func test_consumeMagicLogin_consentAfterPasswordSetup() async throws {
        MockHTTP.handler = { request in
            if routePath(request.url) == "/api/auth/me/" {
                return MockHTTP.json(200, self.meJSON(needsGuidelinesConsent: true))
            }
            return MockHTTP.json(200, ["access": "new-access"])
        }
        let model = MagicConsumeModel(token: "tok", client: makeClient())
        await model.consume()
        XCTAssertEqual(model.state, .ready(.consent))
    }

    func test_consumeMagicLogin_badTokenExpiresWithoutSaving() async throws {
        let tokens = MemoryTokenStore()
        MockHTTP.handler = { _ in
            MockHTTP.json(400, ["detail": [["code": "auth.magic_link_invalid_or_expired"]]])
        }
        let model = MagicConsumeModel(token: "bad", client: makeClient(tokens))
        let session = AuthSession(client: model.client)
        await model.consume()
        XCTAssertNil(try tokens.load())
        XCTAssertEqual(model.state, .expired)
        XCTAssertNil(model.user)
        XCTAssertFalse(model.apply(to: session))
        XCTAssertNil(session.user)
    }

    func test_consumeMagicLogin_usedTokenExpiresWithoutSaving() async throws {
        let tokens = MemoryTokenStore()
        MockHTTP.handler = { _ in
            MockHTTP.json(400, ["detail": [["code": "auth.magic_link_already_used"]]])
        }
        let model = MagicConsumeModel(token: "used", client: makeClient(tokens))
        await model.consume()
        XCTAssertNil(try tokens.load())
        XCTAssertEqual(model.state, .expired)
    }

    func test_consumeMagicLogin_crossUserKeepsSession() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("old-access")
        let paths = PathLog()
        MockHTTP.handler = { request in
            paths.add(routePath(request.url))
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer old-access")
            return MockHTTP.json(403, ["detail": [["code": "auth.already_signed_in_as_different_user"]]])
        }
        let model = MagicConsumeModel(token: "other", client: makeClient(tokens))
        let session = AuthSession(client: model.client)
        session.signedIn(try user(id: "current"))
        await model.consume()
        XCTAssertEqual(paths.values, ["/api/auth/magic-login/other/"])
        XCTAssertEqual(try tokens.load(), "old-access")
        XCTAssertEqual(model.state, .crossUser)
        XCTAssertNil(model.user)
        XCTAssertFalse(model.apply(to: session))
        XCTAssertEqual(session.user?.id, "current")
    }

    func test_consumeMagicLogin_meFailureKeepsOldToken() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("old-access")
        MockHTTP.handler = { request in
            if routePath(request.url).contains("magic-login") {
                return MockHTTP.json(200, ["access": "new-access"])
            }
            return MockHTTP.json(500, [:])
        }
        let model = MagicConsumeModel(token: "tok", client: makeClient(tokens))
        await model.consume()
        XCTAssertEqual(try tokens.load(), "old-access")
        XCTAssertEqual(model.state, .expired)
        XCTAssertNil(model.user)
    }

    func test_consumeMagicLogin_firesOnce() async {
        let hits = PathLog()
        MockHTTP.handler = { request in
            if routePath(request.url).contains("magic-login") {
                hits.add("magic")
                return MockHTTP.json(200, ["access": "new-access"])
            }
            return MockHTTP.json(200, self.meJSON())
        }
        let model = MagicConsumeModel(token: "tok", client: makeClient())
        await model.consume()
        await model.consume()
        XCTAssertEqual(hits.values, ["magic"])
    }

    func test_magicConsumeCopy_matchesWebAndIsLowercase() {
        let lines = [
            MagicConsumeCopy.signingIn,
            MagicConsumeCopy.holdTight,
            MagicConsumeCopy.expiredTitle,
            MagicConsumeCopy.expiredSubtitle,
            MagicConsumeCopy.signInWithPassword,
            MagicConsumeCopy.alreadySignedIn,
            MagicConsumeCopy.differentAccount,
            MagicConsumeCopy.logOutFirst,
            MagicConsumeCopy.backToCalendar,
        ]
        XCTAssertEqual(lines, lines.map { $0.lowercased() })
        XCTAssertEqual(MagicConsumeCopy.signingIn, "signing you in…")
        XCTAssertEqual(MagicConsumeCopy.holdTight, "hold tight 🌿")
        XCTAssertEqual(MagicConsumeCopy.expiredTitle, "link expired")
        XCTAssertEqual(MagicConsumeCopy.expiredSubtitle, "this login link didn't work")
        XCTAssertEqual(MagicConsumeCopy.signInWithPassword, "sign in with your password")
        XCTAssertEqual(MagicConsumeCopy.alreadySignedIn, "already signed in")
        XCTAssertEqual(MagicConsumeCopy.differentAccount, "this link is for a different account")
        XCTAssertEqual(MagicConsumeCopy.logOutFirst, "log out first, then open the link again")
        XCTAssertEqual(MagicConsumeCopy.backToCalendar, "back to calendar")
        XCTAssertFalse(lines.contains("send me a new link"))
    }

    func test_magicLoginToken_setsPendingConsume() {
        XCTAssertEqual(magicLoginToken(from: URL(string: "https://pda.test/magic-login/tok")!), "tok")
        XCTAssertEqual(magicLoginToken(from: URL(string: "https://pda.test/magic-login/tok/")!), "tok")
        XCTAssertNil(magicLoginToken(from: URL(string: "https://pda.test/login")!))
        XCTAssertNil(magicLoginToken(from: URL(string: "https://pda.test/magic-login")!))
        let session = AuthSession(client: makeClient())
        session.open(URL(string: "https://pda.test/magic-login/tok")!)
        XCTAssertEqual(session.pendingMagicToken, "tok")
        session.open(URL(string: "https://pda.test/calendar")!)
        XCTAssertEqual(session.pendingMagicToken, "tok")
    }

    private func meJSON(
        id: String = "user-1",
        firstName: String = "ada",
        email: String = "ada@pda.test",
        needsOnboarding: Bool = false,
        needsPasswordReset: Bool = false,
        needsGuidelinesConsent: Bool = false
    ) -> [String: Any] {
        [
            "id": id,
            "first_name": firstName,
            "email": email,
            "needs_onboarding": needsOnboarding,
            "needs_password_reset": needsPasswordReset,
            "needs_guidelines_consent": needsGuidelinesConsent,
        ]
    }

    private func user(id: String) throws -> SessionUser {
        try Event.decoder.decode(SessionUser.self, from: JSONSerialization.data(withJSONObject: meJSON(id: id)))
    }

    private func makeClient(_ tokens: MemoryTokenStore = MemoryTokenStore()) -> SessionClient {
        SessionClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private final class PathLog: @unchecked Sendable {
    private let lock = NSLock()
    private var paths: [String] = []

    func add(_ path: String) {
        lock.lock()
        paths.append(path)
        lock.unlock()
    }

    var values: [String] {
        lock.lock()
        defer { lock.unlock() }
        return paths
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
