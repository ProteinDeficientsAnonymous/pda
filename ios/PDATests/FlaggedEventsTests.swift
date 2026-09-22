import XCTest

@testable import PDA

final class FlaggedEventsTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_flaggedEventsURL_defaultsToPending() {
        let pending = flaggedEventsURL(base: base)
        XCTAssertEqual(pending.absoluteString, "https://pda.test/api/community/event-flags/?status=pending")
        let all = flaggedEventsURL(base: base, status: "all")
        XCTAssertEqual(all.absoluteString, "https://pda.test/api/community/event-flags/")
        XCTAssertNil(all.query)
    }

    func test_flaggedEvents_getsPendingListWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/event-flags/")
            XCTAssertEqual(request.url?.query, "status=pending")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                flagJSON(id: "f1", title: "Potluck", name: "Ada", reason: "spam", status: "pending"),
            ])
        }
        let rows = try await makeClient(tokens).flaggedEvents()
        XCTAssertEqual(rows.map(\.id), ["f1"])
        XCTAssertEqual(rows[0].eventTitle, "Potluck")
        XCTAssertEqual(rows[0].flaggedByName, "Ada")
        XCTAssertEqual(rows[0].reason, "spam")
        XCTAssertEqual(rows[0].status, "pending")
    }

    func test_flaggedEvents_allOmitsStatusQuery() async throws {
        MockHTTP.handler = { request in
            XCTAssertNil(request.url?.query)
            return MockHTTP.json(200, [])
        }
        let rows = try await makeClient().flaggedEvents(status: "all")
        XCTAssertTrue(rows.isEmpty)
    }

    func test_flaggedEvents_403WithoutManageEvents() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().flaggedEvents()
            XCTFail("403 should not return the list")
        } catch FlaggedEventsError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_flaggedEventsModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = FlaggedEventsModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.rows.isEmpty)
        XCTAssertEqual(model.explanationTitle, FlaggedEventsCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, FlaggedEventsCopy.forbiddenBody)
    }

    func test_flaggedEventMeta_isLowercase() {
        let row = FlaggedEventRow(
            id: "f1",
            eventId: "e1",
            eventTitle: "Potluck",
            flaggedByName: "Ada",
            reason: "Spam",
            status: "pending",
            createdAt: "2026-03-01T18:00:00Z"
        )
        let meta = flaggedEventMeta(row)
        XCTAssertTrue(meta.hasPrefix("flagged by ada"))
        XCTAssertEqual(meta, meta.lowercased())
    }

    func test_flaggedEventsTile_opensListOnly() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "manage_events",
            "manage_users",
            "approve_join_requests",
        ]))
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .flaggedEvents }.map(\.id), ["flagged-events"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .events }.map(\.id), ["events"])
        XCTAssertTrue(tiles.filter { adminHubDestination(for: $0) == nil }.map(\.id).contains("attendance"))
    }

    func test_flaggedEventsCopy_isLowercase() {
        let blobs = [
            FlaggedEventsCopy.title,
            FlaggedEventsCopy.loading,
            FlaggedEventsCopy.error,
            FlaggedEventsCopy.empty,
            FlaggedEventsCopy.forbiddenTitle,
            FlaggedEventsCopy.forbiddenBody,
        ] + FlaggedEventsCopy.filters
        XCTAssertEqual(FlaggedEventsCopy.title, "flagged events")
        XCTAssertEqual(FlaggedEventsCopy.error, "couldn't load flags — try refreshing")
        XCTAssertEqual(FlaggedEventsCopy.empty, "nothing here 🌿")
        XCTAssertEqual(FlaggedEventsCopy.filters, ["pending", "actioned", "dismissed", "all"])
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

private func flagJSON(id: String, title: String, name: String, reason: String, status: String) -> [String: Any] {
    [
        "id": id,
        "event_id": "e1",
        "event_title": title,
        "flagged_by_id": "u1",
        "flagged_by_name": name,
        "reason": reason,
        "status": status,
        "created_at": "2026-03-01T18:00:00Z",
        "reviewed_at": NSNull(),
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
