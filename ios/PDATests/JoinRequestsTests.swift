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

    func test_approveJoinRequest_patchesApprovedStatus() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTAssertEqual(routePath(request.url), "/api/community/join-requests/jr-1/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                let body = try JSONDecoder().decode(JoinDecisionBody.self, from: request.httpBody ?? Data())
                XCTAssertEqual(body.status, "approved")
                return MockHTTP.json(200, [
                    "id": "jr-1",
                    "full_name": "Ada Lovelace",
                    "first_name": "Ada",
                    "phone_number": "+15555550100",
                    "status": "approved",
                    "magic_link_token": "tok",
                    "user_id": "user-9",
                ])
            }
            return MockHTTP.json(200, [
                requestJSON(id: "jr-1", name: "Ada Lovelace", status: "pending", submitted: "2026-03-01T00:00:00Z"),
            ])
        }
        let model = JoinRequestsModel(client: makeClient(tokens))
        await model.load()
        let row = try XCTUnwrap(model.rows.first)
        model.askApprove(row)
        XCTAssertEqual(model.pendingApprove?.id, "jr-1")
        XCTAssertEqual(
            joinRequestApproveMessage(joinRequestApproveName(row)),
            "approve Ada Lovelace? once you approve someone you can't un-approve them — are you sure?"
        )
        await model.confirmApprove(row)
        XCTAssertNil(model.pendingApprove)
        XCTAssertEqual(model.rows.first?.status, "approved")
        XCTAssertNil(model.actionError)
    }

    func test_approveJoinRequest_403WithoutApprovePermission() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "update_join_request_status"]]])
            }
            return MockHTTP.json(200, [
                requestJSON(id: "jr-1", name: "Ada", status: "pending", submitted: "2026-03-01T00:00:00Z"),
            ])
        }
        let model = JoinRequestsModel(client: makeClient())
        await model.load()
        let row = try XCTUnwrap(model.rows.first)
        await model.confirmApprove(row)
        XCTAssertEqual(model.rows.first?.status, "pending")
        XCTAssertFalse(model.forbidden)
        XCTAssertEqual(model.actionError, "couldn't complete that action — try again")
    }

    func test_approveJoinRequest_cancelSkipsPatch() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTFail("cancel should not patch")
            }
            return MockHTTP.json(200, [
                requestJSON(id: "jr-1", name: "Ada", status: "pending", submitted: "2026-03-01T00:00:00Z"),
            ])
        }
        let model = JoinRequestsModel(client: makeClient())
        await model.load()
        let row = try XCTUnwrap(model.rows.first)
        model.askApprove(row)
        model.cancelApprove()
        XCTAssertNil(model.pendingApprove)
        XCTAssertEqual(model.rows.first?.status, "pending")
        let decided = JoinRequestRow(
            id: "jr-2",
            fullName: "",
            phoneNumber: "+15555550100",
            email: "",
            status: "approved",
            submittedAt: "2026-03-01T00:00:00Z"
        )
        model.askApprove(decided)
        XCTAssertNil(model.pendingApprove)
        XCTAssertEqual(joinRequestApproveName(decided), "+15555550100")
    }

    func test_joinRequestApproveCopy_isLowercase() {
        let blobs = [
            JoinRequestApproveCopy.button,
            JoinRequestApproveCopy.title,
            JoinRequestApproveCopy.confirm,
            JoinRequestApproveCopy.cancel,
            JoinRequestApproveCopy.error,
        ]
        XCTAssertEqual(JoinRequestApproveCopy.button, "approve")
        XCTAssertEqual(JoinRequestApproveCopy.title, "approve request")
        XCTAssertEqual(JoinRequestApproveCopy.confirm, "approve")
        XCTAssertEqual(JoinRequestApproveCopy.cancel, "cancel")
        XCTAssertEqual(JoinRequestApproveCopy.error, "couldn't complete that action — try again")
        XCTAssertEqual(
            joinRequestDecisionURL(base: base, id: "jr-1").absoluteString,
            "https://pda.test/api/community/join-requests/jr-1/"
        )
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
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

private struct JoinDecisionBody: Decodable {
    let status: String
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
