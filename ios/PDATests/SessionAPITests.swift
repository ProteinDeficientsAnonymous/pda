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

    func test_keychainTokenStore_savesAndClearsAccessJWT() throws {
        let store = KeychainTokenStore(service: "anonymous.pda.ios.tests", account: "access")
        try store.clear()
        XCTAssertNil(try store.load())
        try store.save("jwt-from-keychain")
        XCTAssertEqual(try store.load(), "jwt-from-keychain")
        try store.clear()
        XCTAssertNil(try store.load())
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

    static func json(_ status: Int, _ body: [String: Any], headers: [String: String] = [:]) -> (Int, Data, [String: String]) {
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
