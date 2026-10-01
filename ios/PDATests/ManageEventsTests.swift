import XCTest

@testable import PDA

final class ManageEventsTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_manageEventsURL_matchesWebList() {
        let url = manageEventsURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/events/")
        XCTAssertNil(url.query)
    }

    func test_manageEvents_getsListWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/events/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                eventJSON(id: "e1", title: "Potluck", status: "active", past: false, start: "2026-05-01T18:00:00Z"),
            ])
        }
        let rows = try await makeClient(tokens).manageEvents()
        XCTAssertEqual(rows.map(\.id), ["e1"])
        XCTAssertEqual(rows[0].title, "Potluck")
        XCTAssertEqual(rows[0].status, "active")
        XCTAssertEqual(rows[0].location, "park")
        XCTAssertEqual(rows[0].eventType, "official")
        XCTAssertFalse(rows[0].isPast)
    }

    func test_manageEvents_403WithoutManageEvents() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().manageEvents()
            XCTFail("403 should not return the list")
        } catch ManageEventsError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_manageEventsModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = ManageEventsModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.rows.isEmpty)
        XCTAssertEqual(model.explanationTitle, ManageEventsCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, ManageEventsCopy.forbiddenBody)
    }

    func test_visibleManageEvents_defaultsToUpcomingByDate() {
        let rows = [
            manageRow(id: "late", title: "Zulu", status: "active", past: false, start: "2026-06-01T00:00:00Z", type: "official"),
            manageRow(id: "early", title: "Ada potluck", status: "active", past: false, start: "2026-01-01T00:00:00Z", type: "community"),
            manageRow(id: "mid", title: "Bee club", status: "active", past: false, start: "2026-03-01T00:00:00Z", type: "club"),
            manageRow(id: "past", title: "Old", status: "active", past: true, start: "2025-01-01T00:00:00Z", type: "club", legacy: true),
            manageRow(id: "draft", title: "Draft night", status: "draft", past: false, start: "", type: "community", tbd: true),
            manageRow(id: "cancelled", title: "Nope", status: "cancelled", past: false, start: "2026-08-01T00:00:00Z", type: "community", partiful: true),
        ]
        XCTAssertEqual(visibleManageEvents(rows).map(\.id), ["early", "mid", "late"])
        XCTAssertEqual(visibleManageEvents(rows, bucket: "past").map(\.id), ["past"])
        XCTAssertEqual(visibleManageEvents(rows, bucket: "drafts").map(\.id), ["draft"])
        XCTAssertEqual(visibleManageEvents(rows, bucket: "cancelled").map(\.id), ["cancelled"])
        XCTAssertEqual(visibleManageEvents(rows, query: "  BEE ").map(\.id), ["mid"])
        XCTAssertEqual(visibleManageEvents(rows, sort: "title").map(\.id), ["early", "mid", "late"])
        XCTAssertEqual(visibleManageEvents(rows, sort: "type").map(\.id), ["mid", "early", "late"])
        XCTAssertEqual(manageEventsEmptyMessage(), ManageEventsCopy.empty)
        XCTAssertEqual(manageEventSubtitle(rows[4]), "tbd")
    }

    func test_eventsTile_opensManageListOnly() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "manage_events",
            "manage_users",
            "approve_join_requests",
        ]))
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .events }.map(\.id), ["events"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .members }.map(\.id), ["members"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .joinRequests }.map(\.id), ["join-requests"])
        let closed = tiles.filter { adminHubDestination(for: $0) == nil }.map(\.id)
        XCTAssertEqual(closed, [])
    }

    func test_manageEventsCopy_isLowercase() {
        let blobs = [
            ManageEventsCopy.title,
            ManageEventsCopy.loading,
            ManageEventsCopy.error,
            ManageEventsCopy.empty,
            ManageEventsCopy.search,
            ManageEventsCopy.forbiddenTitle,
            ManageEventsCopy.forbiddenBody,
            ManageEventsCopy.official,
            ManageEventsCopy.club,
            ManageEventsCopy.partiful,
            ManageEventsCopy.legacy,
        ] + ManageEventsCopy.buckets + ManageEventsCopy.sorts
        XCTAssertEqual(ManageEventsCopy.title, "manage events")
        XCTAssertEqual(ManageEventsCopy.error, "couldn't load events — try refreshing")
        XCTAssertEqual(ManageEventsCopy.empty, "nothing in this bucket")
        XCTAssertEqual(ManageEventsCopy.buckets, ["upcoming", "past", "drafts", "cancelled"])
        XCTAssertEqual(ManageEventsCopy.sorts, ["date", "title", "type"])
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func user(permissions: [String]) throws -> SessionUser {
        let payload: [String: Any] = [
            "id": "user-1",
            "is_member": true,
            "permissions": permissions,
            "roles": [],
        ]
        return try JSONDecoder().decode(SessionUser.self, from: JSONSerialization.data(withJSONObject: payload))
    }
}

private func manageRow(
    id: String,
    title: String,
    status: String,
    past: Bool,
    start: String,
    type: String,
    tbd: Bool = false,
    partiful: Bool = false,
    legacy: Bool = false
) -> ManageEventRow {
    ManageEventRow(
        id: id,
        title: title,
        status: status,
        isPast: past,
        startDatetime: start,
        location: "",
        eventType: type,
        datetimeTbd: tbd,
        isPartifulImport: partiful,
        isLegacy: legacy
    )
}

private func eventJSON(id: String, title: String, status: String, past: Bool, start: String) -> [String: Any] {
    [
        "id": id,
        "title": title,
        "status": status,
        "is_past": past,
        "start_datetime": start,
        "location": "park",
        "event_type": "official",
        "datetime_tbd": false,
        "is_partiful_import": false,
        "is_legacy": false,
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
