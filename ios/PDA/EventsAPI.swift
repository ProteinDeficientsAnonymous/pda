import Foundation

struct EventTag: Decodable, Hashable, Identifiable {
    let id: String
    let name: String
    let slug: String
}

struct Event: Decodable, Hashable, Identifiable {
    // Guest UI never reads location/price/hosts/RSVP even when JSON includes them.
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

    enum CodingKeys: String, CodingKey {
        case id, slug, title, description, tags, status, visibility
        case startDatetime = "start_datetime"
        case endDatetime = "end_datetime"
        case datetimeTbd = "datetime_tbd"
        case photoURL = "photo_url"
        case attendingCount = "attending_count"
        case eventType = "event_type"
        case isPartifulImport = "is_partiful_import"
        case isLegacy = "is_legacy"
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

    private static func parseURL(_ raw: String) -> URL? {
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

    var searchableText: String {
        ([title, when, description] + tags + [badge, attending, moreHintTitle, moreHintBody].compactMap { $0 })
            .joined(separator: "\n")
            .lowercased()
    }

    static func make(
        _ event: Event,
        timeZone: TimeZone = .current,
        locale: Locale = .current
    ) -> GuestEventCopy {
        GuestEventCopy(
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
            moreHintTitle: "want to see more?",
            moreHintBody: "location, rsvp, and organizer details are shown once you sign in"
        )
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

    func events() async throws -> [Event] {
        try await fetch(eventsListURL(base: baseURL))
    }

    func event(id: String) async throws -> Event {
        try await fetch(eventDetailURL(base: baseURL, id: id))
    }

    private func fetch<T: Decodable>(_ url: URL) async throws -> T {
        let (data, response) = try await session.data(from: url)
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
