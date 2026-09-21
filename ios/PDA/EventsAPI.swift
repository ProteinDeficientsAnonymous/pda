import Foundation

struct EventTag: Decodable, Hashable, Identifiable {
    let id: String
    let name: String
    let slug: String
}

struct EventGuest: Decodable, Hashable {
    let userId: String
    let name: String
    let status: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case name, status
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        userId = try c.decodeIfPresent(String.self, forKey: .userId) ?? ""
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        status = try c.decodeIfPresent(String.self, forKey: .status) ?? ""
    }
}

struct EventLinkCopy: Equatable, Hashable {
    let label: String
    let url: URL
}

struct Event: Decodable, Hashable, Identifiable {
    let id: String
    let slug: String
    let title: String
    let description: String
    let startDatetime: Date?
    let endDatetime: Date?
    let datetimeTbd: Bool
    let photoURL: URL?
    let attendingCount: Int
    let eventType: String
    let visibility: String
    let status: String
    let isPartifulImport: Bool
    let isLegacy: Bool
    let tags: [EventTag]
    let location: String
    let price: String
    let createdByName: String
    let coHostNames: [String]
    let guests: [EventGuest]
    let whatsappLink: String
    let partifulLink: String
    let otherLink: String
    let venmoLink: String
    let cashappLink: String
    let zelleInfo: String
    let myRsvp: String
    let rsvpEnabled: Bool
    let isPast: Bool

    enum CodingKeys: String, CodingKey {
        case id, slug, title, description, tags, status, visibility, location, price, guests
        case startDatetime = "start_datetime"
        case endDatetime = "end_datetime"
        case datetimeTbd = "datetime_tbd"
        case photoURL = "photo_url"
        case attendingCount = "attending_count"
        case eventType = "event_type"
        case isPartifulImport = "is_partiful_import"
        case isLegacy = "is_legacy"
        case createdByName = "created_by_name"
        case coHostNames = "co_host_names"
        case whatsappLink = "whatsapp_link"
        case partifulLink = "partiful_link"
        case otherLink = "other_link"
        case venmoLink = "venmo_link"
        case cashappLink = "cashapp_link"
        case zelleInfo = "zelle_info"
        case myRsvp = "my_rsvp"
        case rsvpEnabled = "rsvp_enabled"
        case isPast = "is_past"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        slug = try c.decodeIfPresent(String.self, forKey: .slug) ?? ""
        title = try c.decode(String.self, forKey: .title)
        description = try c.decodeIfPresent(String.self, forKey: .description) ?? ""
        startDatetime = Event.parseISODate(try c.decodeIfPresent(String.self, forKey: .startDatetime) ?? "")
        endDatetime = Event.parseISODate(try c.decodeIfPresent(String.self, forKey: .endDatetime) ?? "")
        datetimeTbd = try c.decodeIfPresent(Bool.self, forKey: .datetimeTbd) ?? false
        photoURL = Event.parseURL(try c.decodeIfPresent(String.self, forKey: .photoURL) ?? "")
        attendingCount = try c.decodeIfPresent(Int.self, forKey: .attendingCount) ?? 0
        eventType = try c.decodeIfPresent(String.self, forKey: .eventType) ?? "community"
        visibility = try c.decodeIfPresent(String.self, forKey: .visibility) ?? "public"
        status = try c.decodeIfPresent(String.self, forKey: .status) ?? "active"
        isPartifulImport = try c.decodeIfPresent(Bool.self, forKey: .isPartifulImport) ?? false
        isLegacy = try c.decodeIfPresent(Bool.self, forKey: .isLegacy) ?? false
        tags = try c.decodeIfPresent([EventTag].self, forKey: .tags) ?? []
        location = try c.decodeIfPresent(String.self, forKey: .location) ?? ""
        price = try c.decodeIfPresent(String.self, forKey: .price) ?? ""
        createdByName = try c.decodeIfPresent(String.self, forKey: .createdByName) ?? ""
        coHostNames = try c.decodeIfPresent([String].self, forKey: .coHostNames) ?? []
        guests = try c.decodeIfPresent([EventGuest].self, forKey: .guests) ?? []
        whatsappLink = try c.decodeIfPresent(String.self, forKey: .whatsappLink) ?? ""
        partifulLink = try c.decodeIfPresent(String.self, forKey: .partifulLink) ?? ""
        otherLink = try c.decodeIfPresent(String.self, forKey: .otherLink) ?? ""
        venmoLink = try c.decodeIfPresent(String.self, forKey: .venmoLink) ?? ""
        cashappLink = try c.decodeIfPresent(String.self, forKey: .cashappLink) ?? ""
        zelleInfo = try c.decodeIfPresent(String.self, forKey: .zelleInfo) ?? ""
        myRsvp = try c.decodeIfPresent(String.self, forKey: .myRsvp) ?? ""
        rsvpEnabled = try c.decodeIfPresent(Bool.self, forKey: .rsvpEnabled) ?? false
        isPast = try c.decodeIfPresent(Bool.self, forKey: .isPast) ?? false
    }

    var memberLinks: [EventLinkCopy] {
        [
            ("whatsapp", whatsappLink),
            ("partiful", partifulLink),
            ("link", otherLink),
            ("venmo", venmoLink),
            ("cash app", cashappLink),
        ].compactMap { label, raw in
            guard let url = Event.parseURL(raw) else { return nil }
            return EventLinkCopy(label: label, url: url)
        }
    }

    static func decodeJSON(_ raw: String) throws -> Event {
        try decoder.decode(Event.self, from: Data(raw.utf8))
    }

    static let decoder: JSONDecoder = {
        let decoder = JSONDecoder()
        return decoder
    }()

    static func parseISODate(_ raw: String) -> Date? {
        guard !raw.isEmpty else { return nil }
        let fractional = ISO8601DateFormatter()
        fractional.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        if let date = fractional.date(from: raw) { return date }
        let whole = ISO8601DateFormatter()
        whole.formatOptions = [.withInternetDateTime]
        if let date = whole.date(from: raw) { return date }
        if let date = try? Date(raw, strategy: .iso8601) { return date }
        let posix = DateFormatter()
        posix.locale = Locale(identifier: "en_US_POSIX")
        posix.timeZone = TimeZone(secondsFromGMT: 0)
        posix.dateFormat = "yyyy-MM-dd'T'HH:mm:ss.SSSSSSXXXXX"
        return posix.date(from: raw)
    }

    static func parseURL(_ raw: String) -> URL? {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return nil }
        return URL(string: trimmed)
    }
}

func shouldShowOnCalendar(_ event: Event) -> Bool {
    !event.datetimeTbd && !event.isPartifulImport && !event.isLegacy
}

func formatEventDateTime(
    start: Date?,
    end: Date?,
    datetimeTbd: Bool,
    timeZone: TimeZone = .current,
    locale: Locale = .current
) -> String {
    guard !datetimeTbd, let start else { return "date & time tbd" }
    let startStamp = dateTimeStamp(start, timeZone: timeZone, locale: locale)
    guard let end else { return startStamp }
    var calendar = Calendar(identifier: .gregorian)
    calendar.timeZone = timeZone
    calendar.locale = locale
    if calendar.isDate(start, inSameDayAs: end) {
        return "\(startStamp) – \(timeStamp(end, timeZone: timeZone, locale: locale))"
    }
    return "\(startStamp) → \(dateTimeStamp(end, timeZone: timeZone, locale: locale))"
}

func eventBadgeLabel(status: String, eventType: String, visibility: String) -> String? {
    if status == "cancelled" { return "cancelled" }
    if eventType == "official" { return "official" }
    if eventType == "club" { return "pda club" }
    if visibility == "invite_only" { return "invite only" }
    if visibility == "members_only" { return "members only" }
    return nil
}

private func dateTimeStamp(_ date: Date, timeZone: TimeZone, locale: Locale) -> String {
    formatted(date, "EEE MMM d, h:mm a", timeZone: timeZone, locale: locale)
}

private func timeStamp(_ date: Date, timeZone: TimeZone, locale: Locale) -> String {
    formatted(date, "h:mm a", timeZone: timeZone, locale: locale)
}

private func formatted(_ date: Date, _ format: String, timeZone: TimeZone, locale: Locale) -> String {
    let formatter = DateFormatter()
    formatter.locale = locale
    formatter.timeZone = timeZone
    formatter.dateFormat = format
    return formatter.string(from: date).lowercased()
}

struct GuestEventCopy: Equatable {
    let title: String
    let when: String
    let description: String
    let tags: [String]
    let badge: String?
    let photoURL: URL?
    let attending: String?
    let moreHintTitle: String
    let moreHintBody: String
    let location: String?
    let hosts: [String]
    let price: String?
    let links: [EventLinkCopy]
    let rsvp: [String]
    let zelle: String?
    let myRsvp: String?

    var searchableText: String {
        let extra = [location, price, zelle, myRsvp, moreHintTitle, moreHintBody].compactMap { $0 }
            + hosts + rsvp + links.flatMap { [$0.label, $0.url.absoluteString] }
        return ([title, when, description] + tags + [badge, attending].compactMap { $0 } + extra)
            .joined(separator: "\n")
            .lowercased()
    }

    static func make(
        _ event: Event,
        user: SessionUser? = nil,
        timeZone: TimeZone = .current,
        locale: Locale = .current
    ) -> GuestEventCopy {
        let memberDetails = canSeeMemberEventDetails(user, event: event)
        return GuestEventCopy(
            title: event.title,
            when: formatEventDateTime(
                start: event.startDatetime,
                end: event.endDatetime,
                datetimeTbd: event.datetimeTbd,
                timeZone: timeZone,
                locale: locale
            ),
            description: event.description,
            tags: event.tags.map(\.name),
            badge: eventBadgeLabel(status: event.status, eventType: event.eventType, visibility: event.visibility),
            photoURL: event.photoURL,
            attending: event.attendingCount > 0 ? "\(event.attendingCount) going" : nil,
            moreHintTitle: memberDetails ? "" : "want to see more?",
            moreHintBody: memberDetails ? "" : "location, rsvp, and organizer details are shown once you sign in",
            location: memberDetails && !event.location.isEmpty ? event.location : nil,
            hosts: memberDetails ? uniqueNonEmpty([event.createdByName] + event.coHostNames) : [],
            price: memberDetails && !event.price.isEmpty ? event.price : nil,
            links: memberDetails ? event.memberLinks : [],
            rsvp: memberDetails ? event.guests.map(\.name).filter { !$0.isEmpty } : [],
            zelle: memberDetails && !event.zelleInfo.isEmpty ? event.zelleInfo : nil,
            myRsvp: memberDetails && !event.myRsvp.isEmpty ? event.myRsvp : nil
        )
    }
}

func canSeeMemberEventDetails(_ user: SessionUser?, event: Event) -> Bool {
    guard let user else { return false }
    if user.isMember { return true }
    return event.eventType == "official" || event.eventType == "club"
}

func canPublicRsvp(_ event: Event) -> Bool {
    event.eventType == "official"
        && event.visibility == "public"
        && event.rsvpEnabled
        && event.status != "cancelled"
        && !event.isPast
}

enum PublicRsvpPhoneStatus: String, Decodable, Equatable {
    case member
    case nonMember = "non_member"
    case new
}

enum PublicRsvpCopy {
    static let title = "rsvp"
    static let phoneLabel = "phone number"
    static let firstNameLabel = "first name"
    static let emailLabel = "email"
    static let going = "i'm going"
    static let maybe = "maybe"
    static let submit = "save rsvp"
    static let memberBody = "that number has an account — sign in to rsvp"
    static let myRsvpsTitle = "my rsvps"
    static let empty = "no rsvps on this device yet"
    static let continueButton = "continue"
    static let saved = "you're on the list"
}

struct RsvpTokenStore {
    var defaults: UserDefaults = .standard
    static let key = "pda-rsvp-token"

    func load() -> String? {
        let value = defaults.string(forKey: Self.key) ?? ""
        return value.isEmpty ? nil : value
    }

    func save(_ token: String) {
        defaults.set(token, forKey: Self.key)
    }

    func clear() {
        defaults.removeObject(forKey: Self.key)
    }
}

struct PublicRsvpItem: Equatable {
    let title: String
    let status: String
}

struct PublicRsvpClient {
    var baseURL: URL = APIConfig.baseURL
    var session: URLSession = .shared
    var tokens: RsvpTokenStore = RsvpTokenStore()

    func checkPhone(eventId: String, phone: String) async throws -> PublicRsvpPhoneStatus {
        struct Out: Decodable { let status: PublicRsvpPhoneStatus }
        let data = try await post("/api/community/public/events/\(eventId)/rsvp-phone-check/", [
            "phone_number": phone,
        ])
        return try Event.decoder.decode(Out.self, from: data).status
    }

    func submit(
        eventId: String,
        phone: String,
        firstName: String,
        email: String,
        status: String
    ) async throws -> String {
        struct Out: Decodable { let rsvpToken: String
            enum CodingKeys: String, CodingKey { case rsvpToken = "rsvp_token" }
        }
        let data = try await post("/api/community/public/events/\(eventId)/rsvp/", [
            "phone_number": phone,
            "first_name": firstName,
            "email": email,
            "status": status,
            "last_name": "",
            "website": "",
        ])
        let token = try Event.decoder.decode(Out.self, from: data).rsvpToken
        tokens.save(token)
        return token
    }

    func myRsvps(token: String) async throws -> [PublicRsvpItem] {
        struct Out: Decodable {
            struct Row: Decodable {
                let status: String
                let event: Event
            }
            let rsvps: [Row]
        }
        var comps = URLComponents(
            url: URL(string: "/api/community/public/my-rsvps/", relativeTo: baseURL)!.absoluteURL,
            resolvingAgainstBaseURL: false
        )!
        comps.queryItems = [URLQueryItem(name: "token", value: token)]
        var req = URLRequest(url: comps.url!)
        req.httpMethod = "GET"
        let (data, response) = try await session.data(for: req)
        let http = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(http) else { throw APIError.http(http) }
        return try Event.decoder.decode(Out.self, from: data).rsvps.map {
            PublicRsvpItem(title: $0.event.title, status: $0.status)
        }
    }

    private func post(_ path: String, _ body: [String: String]) async throws -> Data {
        var req = URLRequest(url: URL(string: path, relativeTo: baseURL)!.absoluteURL)
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return data
    }
}

private func uniqueNonEmpty(_ names: [String]) -> [String] {
    var seen = Set<String>()
    return names.filter { name in
        let key = name.lowercased()
        guard !name.isEmpty, !seen.contains(key) else { return false }
        seen.insert(key)
        return true
    }
}

func eventsListURL(base: URL) -> URL {
    URL(string: "/api/community/events/", relativeTo: base)!.absoluteURL
}

func eventDetailURL(base: URL, id: String) -> URL {
    URL(string: "/api/community/events/\(id)/", relativeTo: base)!.absoluteURL
}

func resolveAPIBaseURL(env: String?, plist: String?, fallback: String) -> URL {
    if let env, !env.isEmpty, let url = URL(string: env) { return url }
    if let plist, !plist.isEmpty, let url = URL(string: plist) { return url }
    return URL(string: fallback)!
}

enum APIConfig {
    static var baseURL: URL {
        resolveAPIBaseURL(
            env: ProcessInfo.processInfo.environment["PDA_API_BASE_URL"],
            plist: Bundle.main.object(forInfoDictionaryKey: "PDAAPIBaseURL") as? String,
            fallback: "https://staging-pda.up.railway.app"
        )
    }
}

struct EventsClient {
    var baseURL: URL = APIConfig.baseURL
    var session: URLSession = .shared
    var tokens: (any TokenStore)?

    func events() async throws -> [Event] {
        try await fetch(eventsListURL(base: baseURL))
    }

    func event(id: String) async throws -> Event {
        try await fetch(eventDetailURL(base: baseURL, id: id))
    }

    private func fetch<T: Decodable>(_ url: URL) async throws -> T {
        var req = URLRequest(url: url)
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(T.self, from: data)
    }
}

enum APIError: Error {
    case http(Int)
}

struct SessionError: Error, Equatable {
    let status: Int
    let code: String?

    var message: String {
        switch code {
        case "auth.invalid_credentials":
            return "that phone number and password don't match — try again"
        case "auth.account_archived":
            return "this account is no longer active"
        case "auth.account_paused":
            return "your membership is currently paused"
        case "auth.refresh_token_invalid", "auth.refresh_failed":
            return "your session expired — please sign in again"
        default:
            return status == 401
                ? "your session expired — please sign in again"
                : "couldn't sign in — try again"
        }
    }
}

func apiErrorCode(from data: Data) -> String? {
    struct Envelope: Decodable {
        struct Item: Decodable { let code: String? }
        let detail: [Item]?
    }
    return try? JSONDecoder().decode(Envelope.self, from: data).detail?.first?.code
}
