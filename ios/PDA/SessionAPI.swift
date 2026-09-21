import Foundation
import Security

enum PhoneStatus: String, Decodable, Equatable {
    case member, pending, unknown
}

struct SessionUser: Decodable, Equatable {
    let id: String
    let phoneNumber: String
    let fullName: String
    let isMember: Bool
    let isPaused: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case phoneNumber = "phone_number"
        case fullName = "full_name"
        case isMember = "is_member"
        case isPaused = "is_paused"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        phoneNumber = try c.decodeIfPresent(String.self, forKey: .phoneNumber) ?? ""
        fullName = try c.decodeIfPresent(String.self, forKey: .fullName) ?? ""
        isMember = try c.decodeIfPresent(Bool.self, forKey: .isMember) ?? false
        isPaused = try c.decodeIfPresent(Bool.self, forKey: .isPaused) ?? false
    }
}

enum LoginCopy {
    static let welcomeTitle = "welcome back"
    static let welcomeSubtitle = "sign in to your pda account"
    static let phoneLabel = "phone number"
    static let passwordLabel = "password"
    static let continueButton = "continue"
    static let signInButton = "sign in"
    static let pendingTitle = "under review"
    static let pendingBody =
        "thanks for your patience — someone will reach out once your request has been reviewed."
    static let unknownTitle = "no account for that number"
    static let unknownBody = "pda creates accounts. this app does not sign people up."
    static let backButton = "use a different number"
}

protocol TokenStore: AnyObject {
    func load() throws -> String?
    func save(_ token: String) throws
    func clear() throws
}

enum TokenStoreError: Error {
    case keychain(OSStatus)
}

final class MemoryTokenStore: TokenStore {
    private var token: String?

    func load() throws -> String? { token }
    func save(_ token: String) throws { self.token = token }
    func clear() throws { token = nil }
}

final class KeychainTokenStore: TokenStore {
    let service: String
    let account: String

    init(service: String = "anonymous.pda.ios", account: String = "access") {
        self.service = service
        self.account = account
    }

    func load() throws -> String? {
        var item: CFTypeRef?
        let status = SecItemCopyMatching(
            [
                kSecClass: kSecClassGenericPassword,
                kSecAttrService: service,
                kSecAttrAccount: account,
                kSecReturnData: true,
                kSecMatchLimit: kSecMatchLimitOne,
            ] as CFDictionary,
            &item
        )
        if status == errSecItemNotFound { return nil }
        guard status == errSecSuccess, let data = item as? Data else {
            throw TokenStoreError.keychain(status)
        }
        return String(data: data, encoding: .utf8)
    }

    func save(_ token: String) throws {
        try clear()
        let status = SecItemAdd(
            [
                kSecClass: kSecClassGenericPassword,
                kSecAttrService: service,
                kSecAttrAccount: account,
                kSecValueData: Data(token.utf8),
                kSecAttrAccessible: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly,
            ] as CFDictionary,
            nil
        )
        guard status == errSecSuccess else { throw TokenStoreError.keychain(status) }
    }

    func clear() throws {
        let status = SecItemDelete(
            [
                kSecClass: kSecClassGenericPassword,
                kSecAttrService: service,
                kSecAttrAccount: account,
            ] as CFDictionary
        )
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw TokenStoreError.keychain(status)
        }
    }
}

struct SessionClient {
    var baseURL: URL = APIConfig.baseURL
    var session: URLSession = .shared
    var tokens: any TokenStore

    func checkPhone(_ phone: String) async throws -> PhoneStatus {
        struct Out: Decodable { let status: PhoneStatus }
        let data = try await post("/api/community/check-phone/", ["phone_number": phone])
        return try Event.decoder.decode(Out.self, from: data).status
    }

    func login(phone: String, password: String) async throws {
        struct Out: Decodable { let access: String }
        let data = try await post("/api/auth/login/", [
            "phone_number": phone,
            "password": password,
        ])
        try tokens.save(try Event.decoder.decode(Out.self, from: data).access)
    }

    func me() async throws -> SessionUser {
        try await authorizedGet("/api/auth/me/")
    }

    private func authorizedGet<T: Decodable>(_ path: String, retrying: Bool = false) async throws -> T {
        var req = makeRequest(path, method: "GET")
        if let token = try tokens.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 401, !retrying {
            try await refreshAccess()
            return try await authorizedGet(path, retrying: true)
        }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(T.self, from: data)
    }

    // ponytail: cookie-only refresh; SPA never puts refresh in JSON.
    private func refreshAccess() async throws {
        struct Out: Decodable { let access: String }
        var req = makeRequest("/api/auth/refresh/", method: "POST")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        try tokens.save(try Event.decoder.decode(Out.self, from: data).access)
    }

    private func post(_ path: String, _ body: [String: String]) async throws -> Data {
        var req = makeRequest(path, method: "POST")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return data
    }

    private func makeRequest(_ path: String, method: String) -> URLRequest {
        var req = URLRequest(url: URL(string: path, relativeTo: baseURL)!.absoluteURL)
        req.httpMethod = method
        return req
    }
}

@Observable
final class LoginModel {
    enum Step: Equatable {
        case phone, password, pending, unknown
    }

    var step: Step = .phone
    var phone = ""
    var password = ""
    var error: String?
    var busy = false
    var unknownBody: String { LoginCopy.unknownBody }
    var client: SessionClient

    init(client: SessionClient) {
        self.client = client
    }

    func submitPhone() async {
        error = nil
        busy = true
        defer { busy = false }
        do {
            switch try await client.checkPhone(phone) {
            case .member: step = .password
            case .pending: step = .pending
            case .unknown: step = .unknown
            }
        } catch {
            self.error = "couldn't check your number — try again"
        }
    }

    func signIn() async {
        error = nil
        busy = true
        defer { busy = false }
        do {
            try await client.login(phone: phone, password: password)
        } catch {
            self.error = "couldn't sign in — try again"
        }
    }
}

@Observable
final class AuthSession {
    var user: SessionUser?
    let client: SessionClient

    init(client: SessionClient = SessionClient(tokens: KeychainTokenStore())) {
        self.client = client
        if ProcessInfo.processInfo.arguments.contains("--reset-session") {
            try? client.tokens.clear()
        }
    }

    func restore() async {
        guard (try? client.tokens.load()) != nil else { return }
        user = try? await client.me()
    }

    func signedIn(_ user: SessionUser) {
        self.user = user
    }
}
