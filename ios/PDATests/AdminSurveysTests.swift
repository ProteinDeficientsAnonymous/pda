import XCTest

@testable import PDA

final class AdminSurveysTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_adminSurveysURL_keepsTrailingSlash() {
        let url = adminSurveysURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/surveys/admin/")
        XCTAssertNil(url.query)
    }

    func test_adminSurveys_getsListWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/admin/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [surveyJSON()])
        }
        let surveys = try await makeClient(tokens).adminSurveys()
        XCTAssertEqual(surveys.map(\.title), ["Spring Potluck"])
        XCTAssertEqual(adminSurveyRowLine(surveys[0]), "/spring-potluck · members_only · 2 responses · mar 1, 2026")
        XCTAssertEqual(adminSurveyStatus(surveys[0]), "active")
    }

    func test_adminSurveys_403WithoutManageSurveys() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().adminSurveys()
            XCTFail("403 should not return the list")
        } catch AdminSurveysError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminSurveysModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminSurveysModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.surveys.isEmpty)
        XCTAssertEqual(model.explanationTitle, "surveys")
        XCTAssertEqual(model.explanationBody, "you need permission to manage surveys to see this list.")
    }

    func test_adminSurveysModel_emptyAndClosedRow() async throws {
        MockHTTP.handler = { _ in MockHTTP.json(200, []) }
        let empty = AdminSurveysModel(client: makeClient())
        await empty.load()
        XCTAssertTrue(empty.loaded)
        XCTAssertTrue(empty.surveys.isEmpty)
        XCTAssertNil(empty.error)
        XCTAssertEqual(AdminSurveysCopy.empty, "nothing yet")

        MockHTTP.handler = { _ in
            MockHTTP.json(200, [surveyJSON(active: false, count: 0, visibility: "public", slug: "summer-picnic", title: "Summer Picnic")])
        }
        let closed = AdminSurveysModel(client: makeClient())
        await closed.load()
        XCTAssertEqual(adminSurveyStatus(closed.surveys[0]), "closed")
        XCTAssertEqual(
            adminSurveyRowLine(closed.surveys[0]),
            "/summer-picnic · public · 0 responses · mar 1, 2026"
        )
    }

    func test_adminSurveysModel_loadFailure() async {
        MockHTTP.handler = { _ in MockHTTP.json(500, ["detail": "nope"]) }
        let model = AdminSurveysModel(client: makeClient())
        await model.load()
        XCTAssertEqual(model.error, "couldn't load surveys — try refreshing")
        XCTAssertFalse(model.forbidden)
        XCTAssertTrue(model.surveys.isEmpty)
    }

    func test_surveysTile_hiddenWithoutManageSurveys() throws {
        XCTAssertFalse(adminHubTiles(for: try user(permissions: ["manage_events"])).map(\.label).contains("surveys"))
        let tiles = adminHubTiles(for: try user(permissions: ["manage_surveys"]))
        XCTAssertEqual(tiles.map(\.label), ["surveys"])
        XCTAssertEqual(tiles.map(\.detail), ["build and review surveys + polls"])
        XCTAssertEqual(tiles.map { adminHubDestination(for: $0) }, [.surveys])
    }

    func test_adminSurveysCopy_isLowercase() {
        let blobs = [
            AdminSurveysCopy.title,
            AdminSurveysCopy.loading,
            AdminSurveysCopy.error,
            AdminSurveysCopy.empty,
            AdminSurveysCopy.forbiddenTitle,
            AdminSurveysCopy.forbiddenBody,
            "active",
            "closed",
        ]
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

private func surveyJSON(
    active: Bool = true,
    count: Int = 2,
    visibility: String = "members_only",
    slug: String = "spring-potluck",
    title: String = "Spring Potluck"
) -> [String: Any] {
    [
        "id": "s1",
        "title": title,
        "slug": slug,
        "visibility": visibility,
        "is_active": active,
        "linked_event_id": NSNull(),
        "created_at": "2026-03-01T00:00:00Z",
        "response_count": count,
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
