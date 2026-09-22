import XCTest

@testable import PDA

final class SurveyResponsesTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_surveyResponses_getsWebRowsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            let path = routePath(request.url)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            if path.hasSuffix("/responses/") {
                XCTAssertEqual(request.httpMethod, "GET")
                XCTAssertEqual(path, "/api/community/surveys/srv-1/responses/")
                return MockHTTP.json(200, [wireResponse])
            }
            XCTAssertEqual(path, "/api/community/surveys/srv-1/admin/")
            return MockHTTP.json(200, wireSurvey)
        }
        let model = SurveyResponsesModel(client: makeClient(tokens), surveyId: "srv-1")
        await model.load()
        XCTAssertNil(model.error)
        XCTAssertEqual(model.responses.map(\.id), ["r1"])
        XCTAssertEqual(surveyResponseSubmitter(model.responses[0].userName), "ada")
        XCTAssertEqual(surveyResponseAnswerText(model.responses[0].answers["qt"]?.answer), "great")
        XCTAssertEqual(surveyResponseAnswerText(model.responses[0].answers["qc"]?.answer), "vanilla,choc")
        XCTAssertEqual(
            surveyResponseAnswerText(model.responses[0].answers["qd"]?.answer),
            "2030-01-01T18:00:00+00:00: yes"
        )
        XCTAssertEqual(surveyResponseCountLabel(model.responses.count), "1 response")
        let shown = surveyResponseSubmittedAt(model.responses[0].submittedAt)
        XCTAssertEqual(shown, shown.lowercased())
        XCTAssertEqual(shown, expectedSubmittedAt("2026-01-01T12:00:00Z"))
    }

    func test_surveyResponses_403IsThePermissionGate() async {
        var sawResponses = false
        MockHTTP.handler = { request in
            if routePath(request.url).hasSuffix("/responses/") {
                sawResponses = true
                return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "manage_surveys"]]])
            }
            return MockHTTP.json(200, wireSurvey)
        }
        let model = SurveyResponsesModel(client: makeClient(), surveyId: "srv-1")
        await model.load()
        XCTAssertTrue(sawResponses)
        XCTAssertEqual(model.error, "couldn't load responses — try refreshing")
        XCTAssertTrue(model.responses.isEmpty)
        XCTAssertNil(model.survey)
    }

    func test_surveyResponses_emptyStateAndCopy() async {
        MockHTTP.handler = { request in
            if routePath(request.url).hasSuffix("/responses/") {
                return MockHTTP.json(200, [])
            }
            XCTAssertFalse(routePath(request.url).contains("/tallies/"))
            return MockHTTP.json(200, textOnlySurvey)
        }
        let model = SurveyResponsesModel(client: makeClient(), surveyId: "srv-1")
        await model.load()
        XCTAssertNil(model.error)
        XCTAssertTrue(model.responses.isEmpty)
        XCTAssertEqual(surveyResponseCountLabel(0), "0 responses")
        XCTAssertEqual(surveyResponseCountLabel(2), "2 responses")
        XCTAssertEqual(SurveyResponsesCopy.empty, "no responses yet")
        XCTAssertEqual(SurveyResponsesCopy.submittedBy, "submitted by")
        XCTAssertEqual(SurveyResponsesCopy.at, "at")
        XCTAssertEqual(SurveyResponsesCopy.back, "← back to editor")
        XCTAssertEqual(SurveyResponsesCopy.responses, "responses")
        XCTAssertEqual(SurveyResponsesCopy.loadError, SurveyResponsesCopy.loadError.lowercased())
        XCTAssertEqual(surveyResponseAnswerText(nil), "—")
        XCTAssertEqual(surveyResponseSubmitter(nil), "—")
        let url = surveyResponsesURL(base: base, surveyId: "srv-1")
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/surveys/srv-1/responses/")
        XCTAssertNil(url.query)
    }

    func test_surveyResponses_loadsTalliesForDatetimePoll() async throws {
        var sawTallies = false
        MockHTTP.handler = { request in
            let path = routePath(request.url)
            if path.hasSuffix("/tallies/") {
                sawTallies = true
                XCTAssertEqual(request.httpMethod, "GET")
                return MockHTTP.json(200, [wireTally])
            }
            if path.hasSuffix("/responses/") { return MockHTTP.json(200, []) }
            return MockHTTP.json(200, wireSurvey)
        }
        let model = SurveyResponsesModel(client: makeClient(), surveyId: "srv-1")
        await model.load()
        XCTAssertTrue(sawTallies)
        XCTAssertEqual(model.talliesError, nil)
        XCTAssertEqual(model.tallies.map(\.questionId), ["qd"])
        XCTAssertEqual(model.tallies[0].totalResponses, 1)
        XCTAssertEqual(surveyPollCount(model.tallies[0].tallies["2030-01-01T18:00:00+00:00"] ?? [:], "yes"), 1)
        XCTAssertEqual(surveyPollCount(model.tallies[0].tallies["2030-01-01T18:00:00+00:00"] ?? [:], "maybe"), 0)
        XCTAssertEqual(SurveyResponsesCopy.pollTallies, "poll tallies")
        XCTAssertEqual(SurveyResponsesCopy.talliesError, "couldn't load tallies")
        XCTAssertEqual(SurveyResponsesCopy.option, "option")
        XCTAssertEqual(SurveyResponsesCopy.yes, "yes")
        XCTAssertEqual(SurveyResponsesCopy.maybe, "maybe")
        XCTAssertEqual(surveyPollTallyTotal(1), "total responses recorded: 1")
        XCTAssertEqual(
            surveyPollTallyTitle(questionId: "qd", questions: model.survey?.questions ?? []),
            "availability"
        )
        XCTAssertEqual(surveyFinalizeOptions(model.survey!), ["2030-01-01T18:00:00+00:00"])
    }

    func test_surveyFinalize_postsWinningDatetime() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            let path = routePath(request.url)
            if request.httpMethod == "POST" {
                XCTAssertEqual(path, "/api/community/surveys/srv-1/finalize/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                let body = try JSONDecoder().decode(WinningPayload.self, from: request.httpBody ?? Data())
                XCTAssertEqual(surveyFinalizeWinningDatetime("2030-01-01T18:00:00+00:00"), "2030-01-01T18:00:00.000Z")
                XCTAssertEqual(body.winningDatetime, "2030-01-01T18:00:00.000Z")
                return MockHTTP.json(200, wireSurvey)
            }
            if path.hasSuffix("/tallies/") { return MockHTTP.json(200, [wireTally]) }
            if path.hasSuffix("/responses/") { return MockHTTP.json(200, []) }
            return MockHTTP.json(200, wireSurvey)
        }
        let model = SurveyResponsesModel(client: makeClient(tokens), surveyId: "srv-1")
        await model.load()
        await model.finalize("2030-01-01T18:00:00+00:00")
        XCTAssertEqual(model.notice, "poll finalized 🌱")
        XCTAssertNil(model.finalizeError)
        XCTAssertEqual(SurveyResponsesCopy.finalize, "finalize poll")
        XCTAssertEqual(SurveyResponsesCopy.finalizeTitle, "finalize survey poll")
        XCTAssertEqual(
            SurveyResponsesCopy.finalizeBody,
            "pick the winning datetime. this locks the survey and, if linked, updates the event start time."
        )
        XCTAssertEqual(SurveyResponsesCopy.cancel, "cancel")
        XCTAssertEqual(SurveyResponsesCopy.confirm, "confirm")
        XCTAssertEqual(SurveyResponsesCopy.finalizing, "finalizing…")
    }

    func test_surveyFinalize_invalidOptionDoesNotPost() async {
        MockHTTP.handler = { _ in
            XCTFail("invalid option should not finalize")
            return MockHTTP.json(500, [:])
        }
        let model = SurveyResponsesModel(client: makeClient(), surveyId: "srv-1")
        await model.finalize("not-a-date")
        XCTAssertEqual(model.finalizeError, "pick a valid option")
        XCTAssertNil(surveyFinalizeWinningDatetime("not-a-date"))
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private func expectedSubmittedAt(_ raw: String) -> String {
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.dateFormat = "MMM d, yyyy h:mm a"
    let date = Event.parseISODate(raw)!
    return formatter.string(from: date).lowercased()
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}

private struct WinningPayload: Decodable {
    let winningDatetime: String

    enum CodingKeys: String, CodingKey {
        case winningDatetime = "winning_datetime"
    }
}

private let wireSurvey: [String: Any] = [
    "id": "srv-1",
    "title": "checkin",
    "slug": "checkin",
    "visibility": "public",
    "is_active": true,
    "questions": [
        ["id": "qt", "label": "mood", "field_type": "text", "required": false, "display_order": 0],
        [
            "id": "qc",
            "label": "flavors",
            "field_type": "checkbox",
            "options": ["vanilla", "choc"],
            "required": false,
            "display_order": 1,
        ],
        [
            "id": "qd",
            "label": "availability",
            "field_type": "datetime_poll",
            "options": ["2030-01-01T18:00:00+00:00"],
            "required": false,
            "display_order": 2,
        ],
    ],
    "poll_result": NSNull(),
]

private let textOnlySurvey: [String: Any] = [
    "id": "srv-1",
    "title": "checkin",
    "slug": "checkin",
    "visibility": "public",
    "questions": [
        ["id": "qt", "label": "mood", "field_type": "text", "required": false, "display_order": 0],
    ],
]

private let wireResponse: [String: Any] = [
    "id": "r1",
    "user_id": "u1",
    "user_name": "ada",
    "submitted_at": "2026-01-01T12:00:00Z",
    "answers": [
        "qt": ["label": "mood", "answer": "great"],
        "qc": ["label": "flavors", "answer": "vanilla,choc"],
        "qd": [
            "label": "availability",
            "answer": ["2030-01-01T18:00:00+00:00": "yes"],
        ],
    ],
]

private let wireTally: [String: Any] = [
    "question_id": "qd",
    "tallies": [
        "2030-01-01T18:00:00+00:00": ["yes": 1, "maybe": 0],
    ],
    "total_responses": 1,
]
