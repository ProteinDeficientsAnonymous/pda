import XCTest

@testable import PDA

final class JoinRequestsTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func setUp() {
        super.setUp()
        MockHTTP.handler = nil
    }

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_joinRequestsURL_keepsTrailingSlash() {
        let url = joinRequestsURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/join-requests/")
        XCTAssertNil(url.query)
    }

    func test_joinRequests_getsListWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/join-requests/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                requestJSON(id: "jr-old", name: "Bea", status: "pending", submitted: "2026-01-01T00:00:00Z"),
                requestJSON(id: "jr-new", name: "Ada Lovelace", status: "approved", submitted: "2026-02-01T00:00:00Z"),
            ])
        }
        let rows = try await makeClient(tokens).joinRequests()
        XCTAssertEqual(rows.map(\.id), ["jr-old", "jr-new"])
        XCTAssertEqual(rows[1].fullName, "Ada Lovelace")
        XCTAssertEqual(rows[1].phoneNumber, "+15555550100")
        XCTAssertEqual(rows[1].email, "ada@pda.test")
        XCTAssertEqual(rows[1].status, "approved")
    }

    func test_joinRequests_403WithoutApprovePermission() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().joinRequests()
            XCTFail("403 should not return the list")
        } catch JoinRequestsError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_joinRequestsModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = JoinRequestsModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.rows.isEmpty)
        XCTAssertEqual(model.explanationTitle, JoinRequestsCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, JoinRequestsCopy.forbiddenBody)
    }

    func test_visibleJoinRequests_defaultsToPendingNewestFirst() {
        let rows = [
            JoinRequestRow(id: "old", fullName: "Bea", phoneNumber: "+15555550101", email: "bea@pda.test", status: "pending", submittedAt: "2026-01-01T00:00:00Z"),
            JoinRequestRow(id: "new", fullName: "Ada", phoneNumber: "+15555550100", email: "ada@pda.test", status: "pending", submittedAt: "2026-03-01T00:00:00Z"),
            JoinRequestRow(id: "approved", fullName: "Cy", phoneNumber: "", email: "cy@pda.test", status: "approved", submittedAt: "2026-04-01T00:00:00Z"),
        ]
        XCTAssertEqual(visibleJoinRequests(rows).map(\.id), ["new", "old"])
        XCTAssertEqual(visibleJoinRequests(rows, filter: "all").map(\.id), ["approved", "new", "old"])
        XCTAssertEqual(visibleJoinRequests(rows, query: "  ADA ").map(\.id), ["new"])
        XCTAssertEqual(visibleJoinRequests(rows, filter: "all", query: "cy@").map(\.id), ["approved"])
        XCTAssertEqual(joinRequestsEmptyMessage(query: ""), JoinRequestsCopy.empty)
        XCTAssertEqual(joinRequestsEmptyMessage(query: "zzz"), JoinRequestsCopy.noMatch)
    }

    func test_joinRequestsTile_opensListOnly() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "manage_users",
            "approve_join_requests",
            "manage_events",
        ]))
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .joinRequests }.map(\.id), ["join-requests"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .members }.map(\.id), ["members"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == nil }.map(\.id), [])
    }

    func test_joinRequestsCopy_isLowercase() {
        let blobs = [
            JoinRequestsCopy.title,
            JoinRequestsCopy.loading,
            JoinRequestsCopy.error,
            JoinRequestsCopy.empty,
            JoinRequestsCopy.noMatch,
            JoinRequestsCopy.forbiddenTitle,
            JoinRequestsCopy.forbiddenBody,
            JoinRequestsCopy.search,
        ] + JoinRequestsCopy.filters
        XCTAssertEqual(JoinRequestsCopy.title, "join requests")
        XCTAssertEqual(JoinRequestsCopy.error, "couldn't load join requests — try refreshing")
        XCTAssertEqual(JoinRequestsCopy.empty, "nothing here 🌿")
        XCTAssertEqual(JoinRequestsCopy.filters, ["all", "pending", "tentative", "approved", "rejected"])
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

private func requestJSON(id: String, name: String, status: String, submitted: String) -> [String: Any] {
    [
        "id": id,
        "full_name": name,
        "phone_number": "+15555550100",
        "email": "ada@pda.test",
        "status": status,
        "submitted_at": submitted,
        "answers": [],
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
