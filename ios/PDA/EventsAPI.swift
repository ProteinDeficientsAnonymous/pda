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
    let attendance: String

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case name, status, attendance
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        userId = try c.decodeIfPresent(String.self, forKey: .userId) ?? ""
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        status = try c.decodeIfPresent(String.self, forKey: .status) ?? ""
        attendance = try c.decodeIfPresent(String.self, forKey: .attendance) ?? ""
    }
}

struct EventRsvpQuestion: Decodable, Hashable, Identifiable {
    let id: String
    let label: String
    let fieldType: String
    let required: Bool
    let options: [String]

    enum CodingKeys: String, CodingKey {
        case id, label, required, options
        case fieldType = "field_type"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        label = try c.decodeIfPresent(String.self, forKey: .label) ?? ""
        fieldType = try c.decodeIfPresent(String.self, forKey: .fieldType) ?? "textarea"
        required = try c.decodeIfPresent(Bool.self, forKey: .required) ?? false
        options = try c.decodeIfPresent([String].self, forKey: .options) ?? []
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
    let coHostIds: [String]
    let hasPoll: Bool
    let myPendingCohostInviteId: String?
    let invitePermission: String
    let invitedUserIds: [String]
    let rsvpQuestions: [EventRsvpQuestion]

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
        case coHostIds = "co_host_ids"
        case hasPoll = "has_poll"
        case myPendingCohostInviteId = "my_pending_cohost_invite_id"
        case invitePermission = "invite_permission"
        case invitedUserIds = "invited_user_ids"
        case rsvpQuestions = "rsvp_questions"
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
        coHostIds = try c.decodeIfPresent([String].self, forKey: .coHostIds) ?? []
        hasPoll = try c.decodeIfPresent(Bool.self, forKey: .hasPoll) ?? false
        let inviteId = try c.decodeIfPresent(String.self, forKey: .myPendingCohostInviteId) ?? ""
        myPendingCohostInviteId = inviteId.isEmpty ? nil : inviteId
        invitePermission = try c.decodeIfPresent(String.self, forKey: .invitePermission) ?? ""
        invitedUserIds = try c.decodeIfPresent([String].self, forKey: .invitedUserIds) ?? []
        rsvpQuestions = try c.decodeIfPresent([EventRsvpQuestion].self, forKey: .rsvpQuestions) ?? []
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

func isHosting(_ event: Event, userId: String) -> Bool {
    event.coHostIds.contains(userId)
}

func canEditEvent(_ event: Event, user: SessionUser?) -> Bool {
    guard let user, user.isMember else { return false }
    return isHosting(event, userId: user.id)
}

func canShowEventComments(_ event: Event, signedIn: Bool, hasGuestToken: Bool) -> Bool {
    event.rsvpEnabled && (signedIn || hasGuestToken)
}

func canShowEventPoll(_ event: Event, winningDatetime: Date?) -> Bool {
    event.hasPoll && winningDatetime == nil
}

func canShowCohostInvite(_ event: Event) -> Bool {
    event.myPendingCohostInviteId != nil && !event.isPast
}

func cohostInviteMessage(createdByName: String) -> String {
    let who = createdByName.trimmingCharacters(in: .whitespacesAndNewlines)
    return "\((who.isEmpty ? "someone" : who).lowercased()) invited you to co-host"
}

func eventCohostInviteURL(base: URL, eventId: String, inviteId: String, action: String) -> URL {
    URL(
        string: "/api/community/events/\(eventId)/cohost-invites/\(inviteId)/\(action)/",
        relativeTo: base
    )!.absoluteURL
}

func canInviteGuests(_ event: Event, user: SessionUser?) -> Bool {
    guard let user else { return false }
    guard event.rsvpEnabled, !event.isPast, event.status != "cancelled" else { return false }
    if event.coHostIds.contains(user.id) || user.permissions.contains("manage_events") { return true }
    return event.invitePermission == "all_members"
        && (event.myRsvp == "attending" || event.myRsvp == "maybe")
}

func rsvpQuestionsApplyToStatus(_ status: String) -> Bool {
    status == "attending" || status == "waitlisted"
}

func missingRequiredQuestionIds(_ questions: [EventRsvpQuestion], answers: [String: String]) -> [String] {
    questions.filter { $0.required && answers[$0.id]?.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty != false }
        .map(\.id)
}

func canShowMemberRsvp(_ event: Event, signedIn: Bool) -> Bool {
    signedIn && event.rsvpEnabled && !event.isPast && event.status != "cancelled"
}

func eventRsvpURL(base: URL, eventId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/rsvp/", relativeTo: base)!.absoluteURL
}

func isCheckInOpen(_ event: Event, now: Date = .now) -> Bool {
    if event.isPast { return true }
    guard let start = event.startDatetime else { return false }
    return start.timeIntervalSince(now) <= 3600
}

func canShowCheckIn(_ event: Event, user: SessionUser?) -> Bool {
    guard let user, event.rsvpEnabled else { return false }
    return isHosting(event, userId: user.id)
}

func canShowManageRsvps(_ event: Event, user: SessionUser?) -> Bool {
    guard let user, event.rsvpEnabled, !event.isPast else { return false }
    return isHosting(event, userId: user.id)
}

func canShowCheckInReport(_ event: Event, user: SessionUser?, flagOn: Bool) -> Bool {
    guard flagOn, let user, event.isPast else { return false }
    return isHosting(event, userId: user.id)
}

func canShowFlagEvent(user: SessionUser?) -> Bool {
    user?.isMember == true
}

func canShowProfile(user: SessionUser?) -> Bool {
    user != nil
}

func canShowSettings(user: SessionUser?) -> Bool {
    user != nil
}

func eventAttendanceURL(base: URL, eventId: String, userId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/rsvps/\(userId)/attendance/", relativeTo: base)!.absoluteURL
}

func eventGuestRsvpURL(base: URL, eventId: String, userId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/rsvps/\(userId)/rsvp/", relativeTo: base)!.absoluteURL
}

func featureFlagsURL(base: URL) -> URL {
    URL(string: "/api/community/feature-flags/", relativeTo: base)!.absoluteURL
}

func featureFlagURL(base: URL, key: String) -> URL {
    let encoded = key.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? key
    return URL(string: "/api/community/feature-flags/\(encoded)/", relativeTo: base)!.absoluteURL
}

func versionURL(base: URL) -> URL {
    URL(string: "/api/community/version/", relativeTo: base)!.absoluteURL
}

func eventCheckInReportURL(base: URL, eventId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/report/", relativeTo: base)!.absoluteURL
}

func eventFlagURL(base: URL, eventId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/flag/", relativeTo: base)!.absoluteURL
}

func userProfileURL(base: URL, userId: String) -> URL {
    URL(string: "/api/auth/users/\(userId)/profile/", relativeTo: base)!.absoluteURL
}

func calendarTokenURL(base: URL) -> URL {
    URL(string: "/api/community/calendar/token/", relativeTo: base)!.absoluteURL
}

struct CalendarToken: Decodable, Equatable {
    let token: String
    let feedUrl: String

    enum CodingKeys: String, CodingKey {
        case token
        case feedUrl = "feed_url"
    }
}

struct MemberProfile: Decodable, Equatable {
    let id: String
    let name: String
    let bio: String
    let pronouns: String
    let nickname: String
    let phoneNumber: String
    let email: String
    let birthday: Birthday?
    let profilePhotoUrl: String

    enum CodingKeys: String, CodingKey {
        case id
        case name = "full_name"
        case bio, pronouns, nickname
        case phoneNumber = "phone_number"
        case email, birthday
        case profilePhotoUrl = "profile_photo_url"
    }

    init(
        id: String = "",
        name: String,
        bio: String,
        pronouns: String,
        nickname: String,
        phoneNumber: String = "",
        email: String = "",
        birthday: Birthday? = nil,
        profilePhotoUrl: String = ""
    ) {
        self.id = id
        self.name = name
        self.bio = bio
        self.pronouns = pronouns
        self.nickname = nickname
        self.phoneNumber = phoneNumber
        self.email = email
        self.birthday = birthday
        self.profilePhotoUrl = profilePhotoUrl
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        bio = try c.decodeIfPresent(String.self, forKey: .bio) ?? ""
        pronouns = try c.decodeIfPresent(String.self, forKey: .pronouns) ?? ""
        nickname = try c.decodeIfPresent(String.self, forKey: .nickname) ?? ""
        phoneNumber = try c.decodeIfPresent(String.self, forKey: .phoneNumber) ?? ""
        email = try c.decodeIfPresent(String.self, forKey: .email) ?? ""
        birthday = try c.decodeIfPresent(Birthday.self, forKey: .birthday)
        profilePhotoUrl = try c.decodeIfPresent(String.self, forKey: .profilePhotoUrl) ?? ""
    }
}

struct EventFlag: Decodable {
    let id: String

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
    }

    enum CodingKeys: String, CodingKey { case id }
}

struct CheckInReportPerson: Decodable, Hashable {
    let name: String

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
    }

    enum CodingKeys: String, CodingKey { case name }
}

struct CheckInReport: Decodable {
    let attendedCount: Int
    let attended: [CheckInReportPerson]
    let noShows: [CheckInReportPerson]
    let didntGo: [CheckInReportPerson]
    let canceled: [CheckInReportPerson]
    let unmarked: [CheckInReportPerson]

    enum CodingKeys: String, CodingKey {
        case attendedCount = "attended_count"
        case attended
        case noShows = "no_shows"
        case didntGo = "didnt_go"
        case canceled, unmarked
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        attendedCount = try c.decodeIfPresent(Int.self, forKey: .attendedCount) ?? 0
        attended = try c.decodeIfPresent([CheckInReportPerson].self, forKey: .attended) ?? []
        noShows = try c.decodeIfPresent([CheckInReportPerson].self, forKey: .noShows) ?? []
        didntGo = try c.decodeIfPresent([CheckInReportPerson].self, forKey: .didntGo) ?? []
        canceled = try c.decodeIfPresent([CheckInReportPerson].self, forKey: .canceled) ?? []
        unmarked = try c.decodeIfPresent([CheckInReportPerson].self, forKey: .unmarked) ?? []
    }
}

struct FeatureFlagsOut: Decodable {
    let flags: [String: Bool]
}

struct AppVersionOut: Decodable {
    let environment: String
}

struct MemberHit: Decodable, Hashable, Identifiable {
    let id: String
    let name: String

    enum CodingKeys: String, CodingKey {
        case id
        case name = "full_name"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
    }
}

func userSearchURL(base: URL, query: String) -> URL {
    var comps = URLComponents(
        url: URL(string: "/api/auth/users/search/", relativeTo: base)!.absoluteURL,
        resolvingAgainstBaseURL: false
    )!
    comps.queryItems = [URLQueryItem(name: "q", value: query)]
    return comps.url!
}

func eventInvitationsURL(base: URL, eventId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/invitations/", relativeTo: base)!.absoluteURL
}

enum PollVoteChrome: Equatable {
    case login
    case vote
}

func pollVoteChrome(signedIn: Bool) -> PollVoteChrome {
    signedIn ? .vote : .login
}

func mergedPollVotes(current: [String: String], optionId: String, choice: String) -> [String: String] {
    var next = current
    if next[optionId] == choice {
        next.removeValue(forKey: optionId)
    } else {
        next[optionId] = choice
    }
    return next
}

func sortPollOptionsByVotes(_ options: [EventPollOption]) -> [EventPollOption] {
    options.sorted {
        if $0.yesCount != $1.yesCount { return $0.yesCount > $1.yesCount }
        if $0.maybeCount != $1.maybeCount { return $0.maybeCount > $1.maybeCount }
        return ($0.datetime ?? .distantFuture) < ($1.datetime ?? .distantFuture)
    }
}

struct EventPollOption: Decodable, Hashable, Identifiable {
    let id: String
    let datetime: Date?
    let displayOrder: Int
    let yesCount: Int
    let maybeCount: Int
    let noCount: Int

    enum CodingKeys: String, CodingKey {
        case id, datetime
        case displayOrder = "display_order"
        case yesCount = "yes_count"
        case maybeCount = "maybe_count"
        case noCount = "no_count"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        datetime = Event.parseISODate(try c.decodeIfPresent(String.self, forKey: .datetime) ?? "")
        displayOrder = try c.decodeIfPresent(Int.self, forKey: .displayOrder) ?? 0
        yesCount = try c.decodeIfPresent(Int.self, forKey: .yesCount) ?? 0
        maybeCount = try c.decodeIfPresent(Int.self, forKey: .maybeCount) ?? 0
        noCount = try c.decodeIfPresent(Int.self, forKey: .noCount) ?? 0
    }
}

struct EventPoll: Decodable {
    let id: String
    let eventId: String
    let isActive: Bool
    let options: [EventPollOption]
    let winningDatetime: Date?
    let myVotes: [String: String]

    enum CodingKeys: String, CodingKey {
        case id, options
        case eventId = "event_id"
        case isActive = "is_active"
        case winningDatetime = "winning_datetime"
        case myVotes = "my_votes"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        eventId = try c.decodeIfPresent(String.self, forKey: .eventId) ?? ""
        isActive = try c.decodeIfPresent(Bool.self, forKey: .isActive) ?? false
        options = try c.decodeIfPresent([EventPollOption].self, forKey: .options) ?? []
        winningDatetime = Event.parseISODate(try c.decodeIfPresent(String.self, forKey: .winningDatetime) ?? "")
        myVotes = try c.decodeIfPresent([String: String].self, forKey: .myVotes) ?? [:]
    }

    static func decodeJSON(_ raw: String) throws -> EventPoll {
        try Event.decoder.decode(EventPoll.self, from: Data(raw.utf8))
    }
}

func eventPollURL(base: URL, eventId: String, suffix: String = "") -> URL {
    URL(string: "/api/community/events/\(eventId)/poll/\(suffix)", relativeTo: base)!.absoluteURL
}

func commentComposerPrompt(canPost: Bool, reason: String?) -> String? {
    if canPost { return nil }
    return reason == "rsvp_required" ? EventCommentCopy.rsvpRequired : EventCommentCopy.loginRequired
}

func visibleComments(_ list: EventCommentList) -> [EventComment] {
    list.canPost ? list.items : []
}

let reactionEmojis = ["❤️", "😂", "🌱", "🔥", "👍", "😭"]

struct CommentReaction: Decodable, Hashable {
    let emoji: String
    let count: Int
    let reactedByMe: Bool

    enum CodingKeys: String, CodingKey {
        case emoji, count
        case reactedByMe = "reacted_by_me"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        emoji = try c.decodeIfPresent(String.self, forKey: .emoji) ?? ""
        count = try c.decodeIfPresent(Int.self, forKey: .count) ?? 0
        reactedByMe = try c.decodeIfPresent(Bool.self, forKey: .reactedByMe) ?? false
    }
}

struct EventComment: Decodable, Hashable, Identifiable {
    let id: String
    let authorDisplayName: String
    let body: String
    let isDeleted: Bool
    let reactions: [CommentReaction]

    enum CodingKeys: String, CodingKey {
        case id, body, reactions
        case authorDisplayName = "author_display_name"
        case isDeleted = "is_deleted"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        authorDisplayName = try c.decodeIfPresent(String.self, forKey: .authorDisplayName) ?? ""
        body = try c.decodeIfPresent(String.self, forKey: .body) ?? ""
        isDeleted = try c.decodeIfPresent(Bool.self, forKey: .isDeleted) ?? false
        reactions = try c.decodeIfPresent([CommentReaction].self, forKey: .reactions) ?? []
    }
}

struct EventCommentList: Decodable {
    let canPost: Bool
    let cannotPostReason: String?
    let items: [EventComment]

    enum CodingKeys: String, CodingKey {
        case items
        case canPost = "can_post"
        case cannotPostReason = "cannot_post_reason"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        canPost = try c.decodeIfPresent(Bool.self, forKey: .canPost) ?? false
        cannotPostReason = try c.decodeIfPresent(String.self, forKey: .cannotPostReason)
        items = try c.decodeIfPresent([EventComment].self, forKey: .items) ?? []
    }

    static func decodeJSON(_ raw: String) throws -> EventCommentList {
        try Event.decoder.decode(EventCommentList.self, from: Data(raw.utf8))
    }
}

func eventCommentsURL(base: URL, eventId: String, suffix: String = "", guestToken: String? = nil) -> URL {
    let url = URL(string: "/api/community/events/\(eventId)/comments/\(suffix)", relativeTo: base)!.absoluteURL
    guard let guestToken, !guestToken.isEmpty else { return url }
    var comps = URLComponents(url: url, resolvingAgainstBaseURL: false)!
    comps.queryItems = [URLQueryItem(name: "token", value: guestToken)]
    return comps.url!
}

func isMyEvent(_ event: Event, userId: String) -> Bool {
    isHosting(event, userId: userId) || event.myRsvp == "attending" || event.myRsvp == "maybe"
}

enum MyEventsFilter: String, CaseIterable {
    case upcoming, hosting, past, drafts, cancelled
}

func myEvents(_ events: [Event], userId: String, filter: MyEventsFilter) -> [Event] {
    switch filter {
    case .upcoming:
        return events.filter { isMyEvent($0, userId: userId) && !$0.isPast && $0.status == "active" }
            .sorted { ($0.startDatetime ?? .distantFuture) < ($1.startDatetime ?? .distantFuture) }
    case .hosting:
        return myEvents(events, userId: userId, filter: .upcoming).filter { isHosting($0, userId: userId) }
    case .past:
        return events.filter { isMyEvent($0, userId: userId) && $0.isPast && $0.status == "active" }
            .sorted { ($0.startDatetime ?? .distantPast) > ($1.startDatetime ?? .distantPast) }
    case .drafts:
        return events.filter { $0.status == "draft" }
            .sorted { ($0.startDatetime ?? .distantPast) > ($1.startDatetime ?? .distantPast) }
    case .cancelled:
        return events.filter { $0.status == "cancelled" }
            .sorted { ($0.startDatetime ?? .distantPast) > ($1.startDatetime ?? .distantPast) }
    }
}

enum MyEventsCopy {
    static let title = "my events"
    static let upcoming = "upcoming"
    static let hosting = "hosting"
    static let past = "past"
    static let drafts = "drafts"
    static let cancelled = "cancelled"
    static let emptyUpcoming = "nothing coming up — events you're hosting or going to will show up here"
    static let emptyHosting = "nothing you're hosting right now"
    static let emptyPast = "no past events yet"
    static let emptyDrafts = "no drafts saved — start one and we'll keep it here until you publish"
    static let emptyCancelled = "no cancelled events"
}

enum MyRsvpsDestination: Equatable {
    case login, guestRsvps, myEvents
}

func myRsvpsDestination(user: SessionUser?, hasGuestToken: Bool) -> MyRsvpsDestination {
    if user != nil { return .myEvents }
    if hasGuestToken { return .guestRsvps }
    return .login
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

func eventsListURL(base: URL, status: String? = nil) -> URL {
    let url = URL(string: "/api/community/events/", relativeTo: base)!.absoluteURL
    guard let status else { return url }
    var comps = URLComponents(url: url, resolvingAgainstBaseURL: false)!
    comps.queryItems = [URLQueryItem(name: "status", value: status)]
    return comps.url!
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

    func home() async throws -> HomePage {
        try await fetch(homeURL(base: baseURL))
    }

    func updateHome(contentPm: String) async throws -> HomePage {
        try await sendJSON("PATCH", url: homeURL(base: baseURL), body: ["content_pm": contentPm])
    }

    func faq() async throws -> HomePage {
        try await fetch(faqURL(base: baseURL))
    }

    func updateFaq(contentPm: String) async throws -> HomePage {
        try await sendJSON("PATCH", url: faqURL(base: baseURL), body: ["content_pm": contentPm])
    }

    func guidelines() async throws -> HomePage {
        try await fetch(guidelinesURL(base: baseURL))
    }

    func updateGuidelines(contentPm: String) async throws -> HomePage {
        try await sendJSON("PATCH", url: guidelinesURL(base: baseURL), body: ["content_pm": contentPm])
    }

    func donate() async throws -> HomePage {
        try await fetch(donateURL(base: baseURL))
    }

    func updateDonate(contentPm: String) async throws -> HomePage {
        try await sendJSON("PATCH", url: donateURL(base: baseURL), body: ["content_pm": contentPm])
    }

    func volunteer() async throws -> HomePage {
        try await fetch(volunteerURL(base: baseURL))
    }

    func updateVolunteer(contentPm: String) async throws -> HomePage {
        try await sendJSON("PATCH", url: volunteerURL(base: baseURL), body: ["content_pm": contentPm])
    }

    func joinForm() async throws -> [JoinQuestion] {
        var req = URLRequest(url: joinFormURL(base: baseURL))
        req.httpMethod = "GET"
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([JoinQuestion].self, from: data)
            .sorted { $0.displayOrder < $1.displayOrder }
    }

    func submitJoinRequest(
        firstName: String,
        lastName: String,
        phone: String,
        email: String,
        answers: [String: String],
        smsConsent: Bool,
        guidelinesConsent: Bool,
        website: String = ""
    ) async throws {
        var req = URLRequest(url: joinRequestURL(base: baseURL))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "first_name": firstName,
            "last_name": lastName,
            "phone_number": phone,
            "email": email,
            "answers": answers,
            "sms_consent": smsConsent,
            "guidelines_consent": guidelinesConsent,
            "website": website,
        ])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 409, apiErrorCode(from: data) == "join_request.phone_already_invited" {
            throw JoinError.alreadyInvited
        }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
    }

    func events(status: String? = nil) async throws -> [Event] {
        try await fetch(eventsListURL(base: baseURL, status: status))
    }

    func event(id: String) async throws -> Event {
        try await fetch(eventDetailURL(base: baseURL, id: id))
    }

    func create(title: String, start: String, description: String, eventType: String) async throws -> Event {
        var req = URLRequest(url: eventsListURL(base: baseURL))
        req.httpMethod = "POST"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "title": title,
            "description": description,
            "start_datetime": start,
            "event_type": eventType,
        ])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(Event.self, from: data)
    }

    func update(id: String, title: String, start: String, description: String) async throws -> Event {
        var req = URLRequest(url: eventDetailURL(base: baseURL, id: id))
        req.httpMethod = "PATCH"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "title": title,
            "description": description,
            "start_datetime": start,
        ])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(Event.self, from: data)
    }

    func poll(eventId: String) async throws -> EventPoll {
        try await sendJSON("GET", url: eventPollURL(base: baseURL, eventId: eventId))
    }

    func acceptCohostInvite(eventId: String, inviteId: String) async throws -> Event {
        try await sendJSON(
            "POST",
            url: eventCohostInviteURL(base: baseURL, eventId: eventId, inviteId: inviteId, action: "accept")
        )
    }

    func declineCohostInvite(eventId: String, inviteId: String) async throws -> Event {
        try await sendJSON(
            "POST",
            url: eventCohostInviteURL(base: baseURL, eventId: eventId, inviteId: inviteId, action: "decline")
        )
    }

    func searchMembers(query: String) async throws -> [MemberHit] {
        try await sendJSON("GET", url: userSearchURL(base: baseURL, query: query))
    }

    func inviteGuests(eventId: String, userIds: [String]) async throws -> Event {
        try await sendJSON(
            "POST",
            url: eventInvitationsURL(base: baseURL, eventId: eventId),
            body: ["user_ids": userIds]
        )
    }

    func setRsvp(eventId: String, status: String, answers: [String: String]) async throws -> Event {
        try await sendJSON(
            "POST",
            url: eventRsvpURL(base: baseURL, eventId: eventId),
            body: ["status": status, "questionnaire_responses": answers]
        )
    }

    func setAttendance(eventId: String, userId: String, attendance: String) async throws -> Event {
        try await sendJSON(
            "POST",
            url: eventAttendanceURL(base: baseURL, eventId: eventId, userId: userId),
            body: ["attendance": attendance]
        )
    }

    func setGuestRsvp(eventId: String, userId: String, status: String) async throws -> Event {
        try await sendJSON(
            "POST",
            url: eventGuestRsvpURL(base: baseURL, eventId: eventId, userId: userId),
            body: ["status": status]
        )
    }

    func featureFlags() async throws -> [String: Bool] {
        let out: FeatureFlagsOut = try await sendJSON("GET", url: featureFlagsURL(base: baseURL))
        return out.flags
    }

    func appVersion() async throws -> String {
        let out: AppVersionOut = try await sendJSON("GET", url: versionURL(base: baseURL))
        return out.environment
    }

    func setFeatureFlag(_ key: String, enabled: Bool) async throws -> [String: Bool] {
        let out: FeatureFlagsOut = try await sendJSON(
            "PATCH",
            url: featureFlagURL(base: baseURL, key: key),
            body: ["enabled": enabled]
        )
        return out.flags
    }

    func checkInReport(eventId: String) async throws -> CheckInReport {
        try await sendJSON("GET", url: eventCheckInReportURL(base: baseURL, eventId: eventId))
    }

    func flagEvent(eventId: String, reason: String) async throws -> EventFlag {
        try await sendJSON(
            "POST",
            url: eventFlagURL(base: baseURL, eventId: eventId),
            body: ["reason": reason]
        )
    }

    func profile(userId: String) async throws -> MemberProfile {
        try await sendJSON("GET", url: userProfileURL(base: baseURL, userId: userId))
    }

    func calendarToken() async throws -> CalendarToken {
        try await sendJSON("GET", url: calendarTokenURL(base: baseURL))
    }

    func regenerateCalendarToken() async throws -> CalendarToken {
        try await sendJSON("POST", url: calendarTokenURL(base: baseURL))
    }

    func votePoll(eventId: String, votes: [String: String]) async throws -> EventPoll {
        try await sendJSON(
            "POST",
            url: eventPollURL(base: baseURL, eventId: eventId, suffix: "vote/"),
            body: ["votes": votes]
        )
    }

    func comments(eventId: String, guestToken: String? = nil) async throws -> EventCommentList {
        try await sendJSON(
            "GET",
            url: eventCommentsURL(base: baseURL, eventId: eventId, guestToken: guestToken)
        )
    }

    func postComment(eventId: String, body: String, guestToken: String? = nil) async throws -> EventComment {
        try await sendJSON(
            "POST",
            url: eventCommentsURL(base: baseURL, eventId: eventId, guestToken: guestToken),
            body: ["body": body]
        )
    }

    func toggleReaction(
        eventId: String,
        commentId: String,
        emoji: String,
        guestToken: String? = nil
    ) async throws -> EventComment {
        try await sendJSON(
            "POST",
            url: eventCommentsURL(
                base: baseURL,
                eventId: eventId,
                suffix: "\(commentId)/reactions/",
                guestToken: guestToken
            ),
            body: ["emoji": emoji]
        )
    }

    func submitFeedback(
        title: String,
        description: String,
        types: [String],
        route: String,
        userAgent: String
    ) async throws -> FeedbackResult {
        try await sendJSON(
            "POST",
            url: URL(string: "/api/community/feedback/", relativeTo: baseURL)!.absoluteURL,
            body: [
                "title": title,
                "description": description,
                "feedback_types": types,
                "metadata": [
                    "route": route,
                    "user_agent": userAgent,
                    "app_version": "",
                ],
            ]
        )
    }

    private func sendJSON<T: Decodable>(_ method: String, url: URL, body: [String: Any]? = nil) async throws -> T {
        var req = URLRequest(url: url)
        req.httpMethod = method
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(T.self, from: data)
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
