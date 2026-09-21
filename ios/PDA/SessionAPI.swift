import Foundation
import Security

enum PhoneStatus: String, Decodable, Equatable {
    case member, pending, unknown
}

struct Birthday: Decodable, Equatable {
    let month: Int
    let day: Int
    let year: Int?
}

func formatBirthday(_ birthday: Birthday) -> String {
    var calendar = Calendar(identifier: .gregorian)
    calendar.locale = Locale(identifier: "en_US_POSIX")
    let date = calendar.date(from: DateComponents(year: 2000, month: birthday.month, day: birthday.day))!
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.dateFormat = "MMMM d"
    let monthDay = formatter.string(from: date).lowercased()
    guard let year = birthday.year else { return monthDay }
    return "\(monthDay), \(year)"
}

struct SessionUser: Decodable, Equatable {
    let id: String
    let phoneNumber: String
    let fullName: String
    let firstName: String
    let email: String
    let isMember: Bool
    let isPaused: Bool
    let needsOnboarding: Bool
    let needsPasswordReset: Bool
    let needsGuidelinesConsent: Bool
    let needsSmsConsent: Bool
    let needsContactPrivacyConsent: Bool
    let permissions: [String]
    let birthday: Birthday?
    let showPhone: Bool
    let showEmail: Bool
    let showBirthday: Bool
    let hideLastName: Bool
    let profilePhotoUrl: String

    enum CodingKeys: String, CodingKey {
        case id
        case phoneNumber = "phone_number"
        case fullName = "full_name"
        case firstName = "first_name"
        case email
        case isMember = "is_member"
        case isPaused = "is_paused"
        case needsOnboarding = "needs_onboarding"
        case needsPasswordReset = "needs_password_reset"
        case needsGuidelinesConsent = "needs_guidelines_consent"
        case needsSmsConsent = "needs_sms_consent"
        case needsContactPrivacyConsent = "needs_contact_privacy_consent"
        case permissions
        case birthday
        case showPhone = "show_phone"
        case showEmail = "show_email"
        case showBirthday = "show_birthday"
        case hideLastName = "hide_last_name"
        case profilePhotoUrl = "profile_photo_url"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        phoneNumber = try c.decodeIfPresent(String.self, forKey: .phoneNumber) ?? ""
        fullName = try c.decodeIfPresent(String.self, forKey: .fullName) ?? ""
        firstName = try c.decodeIfPresent(String.self, forKey: .firstName) ?? ""
        email = try c.decodeIfPresent(String.self, forKey: .email) ?? ""
        isMember = try c.decodeIfPresent(Bool.self, forKey: .isMember) ?? false
        isPaused = try c.decodeIfPresent(Bool.self, forKey: .isPaused) ?? false
        needsOnboarding = try c.decodeIfPresent(Bool.self, forKey: .needsOnboarding) ?? false
        needsPasswordReset = try c.decodeIfPresent(Bool.self, forKey: .needsPasswordReset) ?? false
        needsGuidelinesConsent = try c.decodeIfPresent(Bool.self, forKey: .needsGuidelinesConsent) ?? false
        needsSmsConsent = try c.decodeIfPresent(Bool.self, forKey: .needsSmsConsent) ?? false
        needsContactPrivacyConsent = try c.decodeIfPresent(Bool.self, forKey: .needsContactPrivacyConsent) ?? false
        permissions = try c.decodeIfPresent([String].self, forKey: .permissions) ?? []
        birthday = try c.decodeIfPresent(Birthday.self, forKey: .birthday)
        showPhone = try c.decodeIfPresent(Bool.self, forKey: .showPhone) ?? false
        showEmail = try c.decodeIfPresent(Bool.self, forKey: .showEmail) ?? false
        showBirthday = try c.decodeIfPresent(Bool.self, forKey: .showBirthday) ?? false
        hideLastName = try c.decodeIfPresent(Bool.self, forKey: .hideLastName) ?? false
        profilePhotoUrl = try c.decodeIfPresent(String.self, forKey: .profilePhotoUrl) ?? ""
    }
}

enum AuthGate: Equatable {
    case newPassword
    case onboarding
    case consent
    case email
}

func authGate(for user: SessionUser?) -> AuthGate? {
    guard let user else { return nil }
    if user.needsOnboarding || user.needsPasswordReset {
        return !user.firstName.isEmpty && !user.email.isEmpty ? .newPassword : .onboarding
    }
    if user.needsGuidelinesConsent || user.needsSmsConsent || user.needsContactPrivacyConsent {
        return .consent
    }
    if user.email.isEmpty { return .email }
    return nil
}

enum MemberChrome: Equatable {
    case login
    case locked(title: String, body: String)
    case open
}

enum MemberLockCopy {
    static let directoryTitle = "members only"
    static let directoryBody = "the directory is for vetted members. you'll see everyone here once you're in."
    static let addEventTitle = "members only"
    static let addEventBody = "adding events is for vetted members. official and club events stay open to you."
}

func directoryChrome(for user: SessionUser?) -> MemberChrome {
    memberChrome(for: user, title: MemberLockCopy.directoryTitle, body: MemberLockCopy.directoryBody)
}

func addEventChrome(for user: SessionUser?) -> MemberChrome {
    memberChrome(for: user, title: MemberLockCopy.addEventTitle, body: MemberLockCopy.addEventBody)
}

func allowedEventTypes(for user: SessionUser) -> [String] {
    guard user.isMember else { return [] }
    var types = ["community"]
    if user.permissions.contains("tag_official_event") { types.append("official") }
    if user.permissions.contains("tag_club_event") { types.append("club") }
    return types
}

enum AddEventCopy {
    static let title = "add event"
    static let titleLabel = "title"
    static let whenLabel = "start"
    static let descriptionLabel = "description"
    static let save = "save event"
    static let typeCommunity = "community"
    static let typeOfficial = "official"
    static let typeClub = "pda club"
}

enum EditEventCopy {
    static let title = "edit event"
    static let save = "save event"
}

enum EventCommentCopy {
    static let title = "comments"
    static let post = "post"
    static let placeholder = "say something…"
    static let rsvpRequired = "rsvp to join the conversation."
    static let loginRequired = "log in to comment."
    static let loadError = "couldn't load comments — try refreshing."
}

enum EventPollCopy {
    static let title = "find a time"
    static let respond = "respond to poll"
    static let signIn = "sign in to vote"
    static let yes = "yes"
    static let maybe = "maybe"
    static let no = "no"
    static let loadError = "couldn't load the poll — try refreshing"
}

enum CohostInviteCopy {
    static let accept = "accept"
    static let decline = "decline"
}

enum InviteCopy {
    static let title = "invite members"
    static let search = "search members"
    static let send = "invite"
    static let cancel = "cancel"
}

enum RsvpQuestionCopy {
    static let title = "questions"
}

enum MemberRsvpCopy {
    static let save = "save"
    static let cantGo = "can't go"
    static let going = "i'm going"
    static let maybe = "maybe"
    static let required = "required"
}

enum CheckInCopy {
    static let title = "check-in"
    static let opensLater = "check-in opens an hour before the event"
    static let attended = "attended"
    static let didntAttend = "didn't attend"
    static let empty = "no rsvps to check in"
}

enum ManageRsvpsCopy {
    static let title = "manage rsvps"
    static let going = "i'm going"
    static let maybe = "maybe"
    static let cantGo = "can't go"
    static let empty = "no rsvps to manage"
}

enum CheckInReportCopy {
    static let title = "check-in report"
    static let attended = "attended"
    static let noShows = "no-shows"
    static let didntGo = "didn't go"
    static let canceled = "canceled"
    static let unmarked = "unmarked"
}

enum FlagEventCopy {
    static let title = "report event"
    static let reason = "reason"
    static let submit = "submit"
    static let prompt = "what's wrong with this event?"
    static let thanks = "thanks — we'll take a look"
}

enum ProfileCopy {
    static let title = "profile"
    static let bio = "bio"
}

enum SettingsCopy {
    static let title = "settings"
    static let privacy = "privacy"
    static let showPhone = "show phone on my profile"
    static let showEmail = "show email on my profile"
    static let showBirthday = "show birthday on my profile"
    static let showLastName = "show my last name to other members"
    static let birthday = "birthday"
    static let uploadPhoto = "upload photo"
    static let changePhoto = "change photo"
    static let addBirthday = "add your birthday"
    static let save = "save"
    static let clear = "clear"
    static let preferNotToSay = "prefer not to say"
}

enum CalendarFeedCopy {
    static let title = "calendar"
    static let feedUrl = "feed url"
    static let copyLink = "copy link"
    static let revoke = "revoke and create new link"
    static let revokeConfirm = "revoke and create new link?"
    static let revokeBody = "this will break any calendar already subscribed to your old link — you'll need to resubscribe everywhere. only do this if your link leaked or you want to revoke shared access."
    static let loading = "loading feed link…"
    static let loadError = "couldn't load calendar feed — try again later"
    static let blurb = "subscribe to the community calendar in apple calendar, google calendar, etc — paste the private url once and it'll stay in sync."
}

enum ChangePasswordCopy {
    static let title = "change password"
    static let current = "current password"
    static let update = "update password"
    static let mismatch = "passwords don't match"
    static let sameAsCurrent = "new password must differ from current"
    static let fail = "couldn't update password — try again"
    static let security = "security"
}

func memberChrome(for user: SessionUser?, title: String, body: String) -> MemberChrome {
    guard let user else { return .login }
    return user.isMember ? .open : .locked(title: title, body: body)
}

enum GateCopy {
    static let newPasswordTitle = "set a new password"
    static let onboardingTitle = "welcome"
    static let consentTitle = "before you continue"
    static let emailTitle = "add your email"
    static let emailBody = "we use email for account recovery and event updates — add yours to stay logged in, or keep browsing logged out"
    static let notNow = "not now"
    static let savePassword = "save password"
    static let firstNameLabel = "first name"
    static let emailLabel = "email"
    static let newPasswordLabel = "new password"
    static let confirmPasswordLabel = "confirm new password"
    static let agreeGuidelines = "i agree to the community guidelines"
    static let agreeSms = "i agree to the sms policy"
    static let agreePrivacy = "i understand how my contact info is shown"
    static let save = "save"
    static let continueButton = "continue"
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

    func completeOnboarding(
        newPassword: String,
        firstName: String? = nil,
        lastName: String? = nil,
        email: String? = nil,
        consentTypes: [String] = []
    ) async throws -> SessionUser {
        var body: [String: Any] = ["new_password": newPassword, "consent_types": consentTypes]
        if let firstName { body["first_name"] = firstName }
        if let lastName { body["last_name"] = lastName }
        if let email { body["email"] = email }
        return try await authorizedJSON("/api/auth/complete-onboarding/", method: "POST", body: body)
    }

    func acceptConsents(_ types: [String]) async throws -> SessionUser {
        try await authorizedJSON("/api/auth/accept-consents/", method: "POST", body: ["consent_types": types])
    }

    func setEmail(_ email: String) async throws -> SessionUser {
        try await updateProfile(["email": email])
    }

    func updateProfile(_ body: [String: Any]) async throws -> SessionUser {
        try await authorizedJSON("/api/auth/me/", method: "PATCH", body: body)
    }

    func uploadPhoto(_ data: Data, mimeType: String, filename: String) async throws -> SessionUser {
        try await authorizedMultipart("/api/auth/me/photo/", data: data, mimeType: mimeType, filename: filename)
    }

    func changePassword(current: String, new: String) async throws {
        try await authorizedDiscard(
            "/api/auth/change-password/",
            method: "POST",
            body: ["current_password": current, "new_password": new]
        )
    }

    func logout() async throws {
        let req = makeRequest("/api/auth/logout/", method: "POST")
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        try throwIfFailed(data, status)
        try tokens.clear()
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
        try throwIfFailed(data, status)
        return try Event.decoder.decode(T.self, from: data)
    }

    private func authorizedJSON(
        _ path: String,
        method: String,
        body: [String: Any],
        retrying: Bool = false
    ) async throws -> SessionUser {
        var req = makeRequest(path, method: method)
        if let token = try tokens.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 401, !retrying {
            try await refreshAccess()
            return try await authorizedJSON(path, method: method, body: body, retrying: true)
        }
        try throwIfFailed(data, status)
        return try Event.decoder.decode(SessionUser.self, from: data)
    }

    private func authorizedDiscard(
        _ path: String,
        method: String,
        body: [String: Any],
        retrying: Bool = false
    ) async throws {
        var req = makeRequest(path, method: method)
        if let token = try tokens.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 401, !retrying {
            try await refreshAccess()
            try await authorizedDiscard(path, method: method, body: body, retrying: true)
            return
        }
        try throwIfFailed(data, status)
    }

    private func authorizedMultipart(
        _ path: String,
        data: Data,
        mimeType: String,
        filename: String,
        retrying: Bool = false
    ) async throws -> SessionUser {
        let boundary = "pda-\(UUID().uuidString)"
        var req = makeRequest(path, method: "POST")
        if let token = try tokens.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        var body = Data()
        func ascii(_ s: String) { body.append(Data(s.utf8)) }
        ascii("--\(boundary)\r\n")
        ascii("Content-Disposition: form-data; name=\"photo\"; filename=\"\(filename)\"\r\n")
        ascii("Content-Type: \(mimeType)\r\n\r\n")
        body.append(data)
        ascii("\r\n--\(boundary)--\r\n")
        req.httpBody = body
        let (responseData, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 401, !retrying {
            try await refreshAccess()
            return try await authorizedMultipart(
                path,
                data: data,
                mimeType: mimeType,
                filename: filename,
                retrying: true
            )
        }
        try throwIfFailed(responseData, status)
        return try Event.decoder.decode(SessionUser.self, from: responseData)
    }

    // ponytail: cookie-only refresh; SPA never puts refresh in JSON.
    private func refreshAccess() async throws {
        struct Out: Decodable { let access: String }
        var req = makeRequest("/api/auth/refresh/", method: "POST")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        try throwIfFailed(data, status)
        try tokens.save(try Event.decoder.decode(Out.self, from: data).access)
    }

    private func post(_ path: String, _ body: [String: String]) async throws -> Data {
        var req = makeRequest(path, method: "POST")
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        try throwIfFailed(data, status)
        return data
    }

    private func throwIfFailed(_ data: Data, _ status: Int) throws {
        guard (200 ..< 300).contains(status) else {
            throw SessionError(status: status, code: apiErrorCode(from: data))
        }
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
        } catch let error as SessionError {
            self.error = error.message
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
        if ProcessInfo.processInfo.arguments.contains("--demo-member") {
            user = try? JSONDecoder().decode(
                SessionUser.self,
                from: Data(#"{"id":"demo","is_member":true,"first_name":"ada","email":"ada@pda.test"}"#.utf8)
            )
        }
    }

    func restore() async {
        guard (try? client.tokens.load()) != nil else { return }
        user = try? await client.me()
    }

    func signedIn(_ user: SessionUser) {
        self.user = user
    }

    func logout() async {
        try? await client.logout()
        try? client.tokens.clear()
        user = nil
    }
}
