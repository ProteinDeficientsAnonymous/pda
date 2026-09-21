import Foundation
import XCTest

@testable import PDA

final class EventsAPITests: XCTestCase {
    private let utc = TimeZone(secondsFromGMT: 0)!
    private let posix = Locale(identifier: "en_US_POSIX")

    func test_decode_publicFields_fromGuestPayload() throws {
        let event = try Event.decodeJSON(Self.guestPayload)
        XCTAssertEqual(event.id, "7e71df73-cd6b-405b-8ee3-852d1eff8b0a")
        XCTAssertEqual(event.slug, "lets-get-donuts")
        XCTAssertEqual(event.title, "lets get donuts")
        XCTAssertEqual(event.description, "come one come all!")
        XCTAssertEqual(event.datetimeTbd, false)
        XCTAssertEqual(event.attendingCount, 2)
        XCTAssertEqual(event.eventType, "official")
        XCTAssertEqual(event.visibility, "public")
        XCTAssertEqual(event.tags.map(\.name), ["Side quest"])
        XCTAssertEqual(event.startDatetime, iso("2026-07-30T16:00:00Z"))
        XCTAssertEqual(event.endDatetime, iso("2026-07-30T18:00:00Z"))
        XCTAssertEqual(event.photoURL?.absoluteString, "https://cdn.example/photo.jpg")
    }

    func test_decode_fractionalAndWholeISODates() throws {
        XCTAssertNotNil(try Event.decodeJSON(Self.fractionalDatePayload).startDatetime)
        XCTAssertNotNil(try Event.decodeJSON(Self.wholeDatePayload).startDatetime)
        XCTAssertNotNil(try Event.decodeJSON(Self.microsecondDatePayload).startDatetime)
    }

    func test_decode_emptyPhotoAndMissingOptionals() throws {
        let event = try Event.decodeJSON(Self.sparsePayload)
        XCTAssertNil(event.photoURL)
        XCTAssertEqual(event.tags, [])
        XCTAssertNil(event.startDatetime)
        XCTAssertEqual(event.description, "")
    }

    func test_calendar_skipsTbdPartifulAndLegacy() throws {
        XCTAssertFalse(shouldShowOnCalendar(try Event.decodeJSON(Self.tbdPayload)))
        XCTAssertFalse(shouldShowOnCalendar(try Event.decodeJSON(Self.partifulPayload)))
        XCTAssertFalse(shouldShowOnCalendar(try Event.decodeJSON(Self.legacyPayload)))
        XCTAssertTrue(shouldShowOnCalendar(try Event.decodeJSON(Self.guestPayload)))
    }

    func test_formatEventDateTime_isLowercase() {
        let start = iso("2024-06-01T18:00:00Z")
        let sameDayEnd = iso("2024-06-01T20:00:00Z")
        let nextDayEnd = iso("2024-06-02T20:00:00Z")
        XCTAssertEqual(
            formatEventDateTime(start: start, end: nil, datetimeTbd: false, timeZone: utc, locale: posix),
            "sat jun 1, 6:00 pm"
        )
        XCTAssertEqual(
            formatEventDateTime(start: start, end: sameDayEnd, datetimeTbd: false, timeZone: utc, locale: posix),
            "sat jun 1, 6:00 pm – 8:00 pm"
        )
        XCTAssertEqual(
            formatEventDateTime(start: start, end: nextDayEnd, datetimeTbd: false, timeZone: utc, locale: posix),
            "sat jun 1, 6:00 pm → sun jun 2, 8:00 pm"
        )
        XCTAssertEqual(
            formatEventDateTime(start: start, end: sameDayEnd, datetimeTbd: true, timeZone: utc, locale: posix),
            "date & time tbd"
        )
        XCTAssertEqual(
            formatEventDateTime(start: nil, end: nil, datetimeTbd: false, timeZone: utc, locale: posix),
            "date & time tbd"
        )
    }

    func test_badge_matchesWebLabels() {
        XCTAssertEqual(eventBadgeLabel(status: "cancelled", eventType: "community", visibility: "public"), "cancelled")
        XCTAssertEqual(eventBadgeLabel(status: "active", eventType: "official", visibility: "public"), "official")
        XCTAssertEqual(eventBadgeLabel(status: "active", eventType: "club", visibility: "public"), "pda club")
        XCTAssertEqual(
            eventBadgeLabel(status: "active", eventType: "community", visibility: "invite_only"),
            "invite only"
        )
        XCTAssertEqual(
            eventBadgeLabel(status: "active", eventType: "community", visibility: "members_only"),
            "members only"
        )
        XCTAssertNil(eventBadgeLabel(status: "active", eventType: "community", visibility: "public"))
    }

    func test_guestCopy_hidesLocationPriceHostsAndRsvp() throws {
        let copy = GuestEventCopy.make(
            try Event.decodeJSON(Self.guestPayload),
            timeZone: utc,
            locale: posix
        )
        let blob = copy.searchableText
        XCTAssertTrue(blob.contains("lets get donuts"))
        XCTAssertTrue(blob.contains("come one come all!"))
        XCTAssertTrue(blob.contains("side quest"))
        XCTAssertTrue(blob.contains("official"))
        XCTAssertTrue(blob.contains("2 going"))
        XCTAssertTrue(blob.contains("want to see more?"))
        XCTAssertFalse(blob.contains("123 main st"))
        XCTAssertFalse(blob.contains("brooklyn"))
        XCTAssertFalse(blob.contains("alice host"))
        XCTAssertFalse(blob.contains("sliding scale"))
        XCTAssertFalse(blob.contains("whatsapp"))
        XCTAssertFalse(blob.contains("venmo"))
        XCTAssertFalse(blob.contains("going: alice"))
        XCTAssertNil(copy.location)
        XCTAssertEqual(copy.hosts, [])
        XCTAssertEqual(copy.links, [])
        XCTAssertEqual(copy.rsvp, [])
    }

    func test_memberCopy_showsLocationHostsLinksAndRsvp() throws {
        let copy = GuestEventCopy.make(
            try Event.decodeJSON(Self.guestPayload),
            user: try sessionUser(isMember: true),
            timeZone: utc,
            locale: posix
        )
        let blob = copy.searchableText
        XCTAssertEqual(copy.location, "123 Main St, Brooklyn, NY")
        XCTAssertEqual(copy.hosts, ["Alice Host", "Bob Host"])
        XCTAssertEqual(copy.price, "sliding scale")
        XCTAssertEqual(copy.links.map(\.label), ["whatsapp", "venmo"])
        XCTAssertEqual(copy.rsvp, ["going: alice"])
        XCTAssertTrue(blob.contains("123 main st"))
        XCTAssertTrue(blob.contains("alice host"))
        XCTAssertTrue(blob.contains("whatsapp"))
        XCTAssertTrue(blob.contains("venmo"))
        XCTAssertTrue(blob.contains("going: alice"))
        XCTAssertEqual(copy.moreHintTitle, "")
    }

    func test_memberCopy_dedupesCreatedByAndCohostsCaseInsensitive() throws {
        let copy = GuestEventCopy.make(
            try Event.decodeJSON("""
            {
              "id": "d",
              "title": "dup",
              "event_type": "official",
              "created_by_name": "Duncan",
              "co_host_names": ["duncan", "Ada"]
            }
            """),
            user: try sessionUser(isMember: true)
        )
        XCTAssertEqual(copy.hosts, ["Duncan", "Ada"])
    }

    func test_tentativeCopy_showsMemberFieldsOnlyOnOfficial() throws {
        let tentative = try sessionUser(isMember: false)
        let official = GuestEventCopy.make(
            try Event.decodeJSON(Self.guestPayload),
            user: tentative,
            timeZone: utc,
            locale: posix
        )
        XCTAssertEqual(official.location, "123 Main St, Brooklyn, NY")
        XCTAssertEqual(official.hosts, ["Alice Host", "Bob Host"])

        let community = GuestEventCopy.make(
            try Event.decodeJSON(
                Self.guestPayload.replacingOccurrences(of: "\"official\"", with: "\"community\"")
            ),
            user: tentative,
            timeZone: utc,
            locale: posix
        )
        XCTAssertNil(community.location)
        XCTAssertEqual(community.hosts, [])
        XCTAssertEqual(community.links, [])
        XCTAssertEqual(community.rsvp, [])
        XCTAssertTrue(community.searchableText.contains("want to see more?"))
        XCTAssertFalse(community.searchableText.contains("123 main st"))
    }

    func test_eventURLs_keepTrailingSlash() {
        let base = URL(string: "https://staging-pda.up.railway.app")!
        XCTAssertEqual(
            eventsListURL(base: base).absoluteString,
            "https://staging-pda.up.railway.app/api/community/events/"
        )
        XCTAssertEqual(
            eventDetailURL(base: base, id: "monthly-meetup").absoluteString,
            "https://staging-pda.up.railway.app/api/community/events/monthly-meetup/"
        )
    }

    func test_apiConfig_prefersEnvThenPlistThenStaging() {
        XCTAssertEqual(
            resolveAPIBaseURL(
                env: "http://127.0.0.1:8000",
                plist: "https://example.invalid",
                fallback: "https://staging-pda.up.railway.app"
            ).absoluteString,
            "http://127.0.0.1:8000"
        )
        XCTAssertEqual(
            resolveAPIBaseURL(
                env: "",
                plist: "https://example.invalid",
                fallback: "https://staging-pda.up.railway.app"
            ).absoluteString,
            "https://example.invalid"
        )
        XCTAssertEqual(
            resolveAPIBaseURL(env: nil, plist: nil, fallback: "https://staging-pda.up.railway.app")
                .absoluteString,
            "https://staging-pda.up.railway.app"
        )
    }

    private func iso(_ raw: String) -> Date {
        Event.parseISODate(raw)!
    }

    private func sessionUser(isMember: Bool) throws -> SessionUser {
        try JSONDecoder().decode(
            SessionUser.self,
            from: try JSONSerialization.data(withJSONObject: [
                "id": "user-1",
                "is_member": isMember,
                "first_name": "ada",
                "email": "ada@pda.test",
            ])
        )
    }
}

extension EventsAPITests {
    static let guestPayload = """
    {
      "id": "7e71df73-cd6b-405b-8ee3-852d1eff8b0a",
      "slug": "lets-get-donuts",
      "title": "lets get donuts",
      "description": "come one come all!",
      "start_datetime": "2026-07-30T16:00:00Z",
      "end_datetime": "2026-07-30T18:00:00Z",
      "datetime_tbd": false,
      "location": "123 Main St, Brooklyn, NY",
      "latitude": 40.7,
      "longitude": -73.9,
      "price": "sliding scale",
      "attending_count": 2,
      "photo_url": "https://cdn.example/photo.jpg",
      "created_by_name": "Alice Host",
      "co_host_names": ["Bob Host"],
      "guests": [{"user_id": "u1", "name": "going: alice", "status": "attending"}],
      "whatsapp_link": "https://chat.whatsapp.com/abc",
      "venmo_link": "https://venmo.com/alice",
      "tags": [{"id": "83cf183c-3d65-45a5-8fb8-bfd8bdb881ee", "name": "Side quest", "slug": "side-quest"}],
      "event_type": "official",
      "visibility": "public",
      "is_legacy": false,
      "is_partiful_import": false,
      "status": "active"
    }
    """

    static let fractionalDatePayload = """
    {
      "id": "a7b0791f-0303-485a-bedf-9bac1efab3b5",
      "slug": "monthly-meetup",
      "title": "Monthly meetup",
      "start_datetime": "2026-09-21T18:59:16.168Z",
      "end_datetime": "2026-09-21T20:59:16.168Z",
      "event_type": "official",
      "visibility": "public"
    }
    """

    static let wholeDatePayload = """
    {
      "id": "0263f85d-1917-434d-af06-e5618cab200c",
      "slug": "side-quest",
      "title": "Side quest",
      "start_datetime": "2026-07-29T16:00:00Z",
      "event_type": "community",
      "visibility": "public"
    }
    """

    static let microsecondDatePayload = """
    {
      "id": "micro",
      "title": "micro",
      "start_datetime": "2026-09-21T18:59:10.139000Z"
    }
    """

    static let sparsePayload = """
    { "id": "x", "title": "untitled" }
    """

    static let tbdPayload = """
    { "id": "tbd", "title": "tbd", "datetime_tbd": true }
    """

    static let partifulPayload = """
    { "id": "p", "title": "import", "is_partiful_import": true }
    """

    static let legacyPayload = """
    { "id": "l", "title": "old", "is_legacy": true }
    """
}
