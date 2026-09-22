import XCTest

@testable import PDA

final class SurveyPageTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_loadSurvey_publicWithoutAuth() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/view/feedback/")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            return MockHTTP.json(200, self.surveyJSON())
        }
        let model = SurveyPageModel(slug: "feedback", client: makeClient())
        await model.load()
        XCTAssertEqual(model.survey?.title, "feedback survey")
        XCTAssertEqual(model.survey?.questions.map(\.id), ["q1", "q2"])
        XCTAssertNil(model.loadError)
        XCTAssertTrue(model.showsForm)
        XCTAssertFalse(model.readOnly)
        XCTAssertEqual(model.submitLabel, "submit")
    }

    func test_loadSurvey_sendsBearerWhenSignedIn() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, self.surveyJSON(membersOnly: true))
        }
        let model = SurveyPageModel(slug: "feedback", client: makeClient(tokens))
        await model.load()
        XCTAssertEqual(model.survey?.visibility, "members_only")
        XCTAssertNil(model.loadError)
    }

    func test_loadSurvey_404ShowsLoadError() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(404, ["detail": [["code": "survey.not_found"]]])
        }
        let model = SurveyPageModel(slug: "missing", client: makeClient())
        await model.load()
        XCTAssertNil(model.survey)
        XCTAssertFalse(model.showsForm)
        XCTAssertEqual(model.loadError, "couldn't load the survey — try refreshing")
    }

    func test_submitSurvey_blocksRequiredThenPostsText() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "POST" {
                XCTAssertEqual(routePath(request.url), "/api/community/surveys/view/feedback/respond/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                let body = try JSONDecoder().decode(SurveyAnswersBody.self, from: request.httpBody ?? Data())
                XCTAssertEqual(body.answers, ["q1": "great job"])
                return MockHTTP.json(201, ["id": "resp-1"])
            }
            return MockHTTP.json(200, self.surveyJSON())
        }
        let model = SurveyPageModel(slug: "feedback", client: makeClient(tokens))
        await model.load()
        await model.submit()
        XCTAssertEqual(model.fieldErrors["q1"], "required")
        XCTAssertFalse(model.saved)
        model.setText("q1", "   ")
        await model.submit()
        XCTAssertEqual(model.fieldErrors["q1"], "required")
        model.setText("q1", "great job")
        model.setText("q2", "  ")
        await model.submit()
        XCTAssertTrue(model.fieldErrors.isEmpty)
        XCTAssertTrue(model.saved)
        XCTAssertNil(model.serverError)
        XCTAssertEqual(model.submitLabel, "submit")
    }

    func test_submitSurvey_preloadsUpdate() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, self.surveyJSON(responseID: "resp-1", answer: "previous answer"))
        }
        let model = SurveyPageModel(slug: "feedback", client: makeClient())
        await model.load()
        XCTAssertEqual(model.submitLabel, "update response")
        XCTAssertEqual(model.textAnswer("q1"), "previous answer")
    }

    func test_closedSurvey_hidesForm() async {
        MockHTTP.handler = { _ in MockHTTP.json(200, self.surveyJSON(active: false)) }
        let model = SurveyPageModel(slug: "feedback", client: makeClient())
        await model.load()
        XCTAssertTrue(model.showsClosed)
        XCTAssertFalse(model.showsForm)
        XCTAssertEqual(model.survey?.title, "feedback survey")
    }

    func test_finalizedPoll_locksForm() async {
        MockHTTP.handler = { _ in MockHTTP.json(200, self.surveyJSON(active: false, finalized: true)) }
        let model = SurveyPageModel(slug: "feedback", client: makeClient())
        await model.load()
        XCTAssertFalse(model.showsClosed)
        XCTAssertTrue(model.showsForm)
        XCTAssertTrue(model.readOnly)
    }

    func test_submitSurvey_closedRefetches() async {
        var gets = 0
        MockHTTP.handler = { request in
            if request.httpMethod == "POST" {
                return MockHTTP.json(400, ["detail": [["code": "survey.closed"]]])
            }
            gets += 1
            return MockHTTP.json(200, self.surveyJSON())
        }
        let model = SurveyPageModel(slug: "feedback", client: makeClient())
        await model.load()
        model.setText("q1", "too late")
        await model.submit()
        XCTAssertEqual(model.serverError, "this survey is closed — responses are no longer accepted")
        XCTAssertFalse(model.saved)
        XCTAssertEqual(model.textAnswer("q1"), "too late")
        XCTAssertEqual(gets, 2)
    }

    func test_submitSurvey_otherFailureUsesFallback() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "POST" { return MockHTTP.json(500, [:]) }
            return MockHTTP.json(200, self.surveyJSON())
        }
        let model = SurveyPageModel(slug: "feedback", client: makeClient())
        await model.load()
        model.setText("q1", "hello")
        await model.submit()
        XCTAssertEqual(model.serverError, "couldn't submit — try again")
        XCTAssertFalse(model.saved)
    }

    func test_surveyAnswerError_emptyPollNeedsAPick() {
        let poll = PublicSurveyQuestion(
            id: "q3",
            label: "when",
            fieldType: "datetime_poll",
            options: ["2030-01-01T10:00:00Z"],
            required: true,
            displayOrder: 2
        )
        XCTAssertEqual(surveyAnswerError(poll, answer: .map([:])), "pick at least one")
        XCTAssertNil(surveyAnswerError(poll, answer: .map(["2030-01-01T10:00:00Z": "yes"])))
    }

    func test_surveyPageCopy_isLowercase() {
        let blobs = [
            SurveyPageCopy.loading,
            SurveyPageCopy.loadError,
            SurveyPageCopy.closed,
            SurveyPageCopy.finalized,
            SurveyPageCopy.submit,
            SurveyPageCopy.update,
            SurveyPageCopy.saving,
            SurveyPageCopy.saved,
            SurveyPageCopy.required,
            SurveyPageCopy.pickOne,
            SurveyPageCopy.selectOne,
            SurveyPageCopy.submitError,
        ]
        XCTAssertEqual(SurveyPageCopy.loading, "loading…")
        XCTAssertEqual(SurveyPageCopy.loadError, "couldn't load the survey — try refreshing")
        XCTAssertEqual(SurveyPageCopy.closed, "this survey is closed — responses are no longer accepted")
        XCTAssertEqual(SurveyPageCopy.finalized, "this poll has been finalized — responses are locked")
        XCTAssertEqual(SurveyPageCopy.submit, "submit")
        XCTAssertEqual(SurveyPageCopy.update, "update response")
        XCTAssertEqual(SurveyPageCopy.saving, "saving…")
        XCTAssertEqual(SurveyPageCopy.saved, "saved ✓")
        XCTAssertEqual(SurveyPageCopy.required, "required")
        XCTAssertEqual(SurveyPageCopy.pickOne, "pick at least one")
        XCTAssertEqual(SurveyPageCopy.selectOne, "select one")
        XCTAssertEqual(SurveyPageCopy.submitError, "couldn't submit — try again")
        XCTAssertEqual(
            publicSurveyURL(base: base, slug: "feedback").absoluteString,
            "https://pda.test/api/community/surveys/view/feedback/"
        )
        XCTAssertEqual(
            publicSurveyRespondURL(base: base, slug: "feedback").absoluteString,
            "https://pda.test/api/community/surveys/view/feedback/respond/"
        )
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func surveyJSON(
        active: Bool = true,
        membersOnly: Bool = false,
        responseID: String? = nil,
        answer: String? = nil,
        finalized: Bool = false
    ) -> [String: Any] {
        var row: [String: Any] = [
            "id": "srv-1",
            "title": "feedback survey",
            "description": "tell us",
            "slug": "feedback",
            "visibility": membersOnly ? "members_only" : "public",
            "is_active": active,
            "questions": [
                [
                    "id": "q2",
                    "label": "more",
                    "field_type": "text",
                    "required": false,
                    "display_order": 1,
                ],
                [
                    "id": "q1",
                    "label": "thoughts",
                    "field_type": "text",
                    "required": true,
                    "display_order": 0,
                ],
            ],
        ]
        if let responseID { row["my_response_id"] = responseID }
        if let answer {
            row["my_answers"] = ["q1": ["label": "thoughts", "answer": answer]]
        }
        if finalized {
            row["poll_result"] = [
                "id": "r1",
                "winning_datetime": "2030-01-01T10:00:00Z",
                "finalized_by_id": NSNull(),
                "finalized_at": "2029-12-01T10:00:00Z",
            ]
        }
        return row
    }
}

private struct SurveyAnswersBody: Decodable {
    let answers: [String: String]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
