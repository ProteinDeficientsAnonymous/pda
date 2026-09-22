import XCTest

@testable import PDA

final class FeedbackTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_showsFeedbackControl_onlyWhenSignedIn() throws {
        XCTAssertFalse(showsFeedbackControl(for: nil))
        XCTAssertTrue(showsFeedbackControl(for: try user()))
    }

    func test_showsFeedbackControl_guestWithRsvpToken() throws {
        XCTAssertFalse(showsFeedbackControl(for: nil, guestToken: nil))
        XCTAssertFalse(showsFeedbackControl(for: nil, guestToken: ""))
        XCTAssertTrue(showsFeedbackControl(for: nil, guestToken: "rsvp-token-123"))
        XCTAssertTrue(showsFeedbackControl(for: try user(), guestToken: nil))
    }

    func test_submitFeedback_guestUsesSameEndpoint() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.absoluteString, "https://pda.test/api/community/feedback/")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            let body = try JSONDecoder().decode(FeedbackBody.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.title, "guest note")
            XCTAssertEqual(body.description, "the map link failed")
            XCTAssertEqual(body.feedbackTypes, ["bug"])
            XCTAssertEqual(body.metadata.route, "/calendar")
            return MockHTTP.json(201, ["html_url": "https://github.com/owner/repo/issues/9"])
        }
        let model = FeedbackModel(client: makeClient(), route: "/calendar", userAgent: "ios-guest")
        model.setTitle("guest note")
        model.setDescription("the map link failed")
        model.bug = true
        await model.submit()
        XCTAssertEqual(model.toast, FeedbackCopy.saved)
        XCTAssertFalse(model.open)
    }

    func test_submitFeedback_postsSignedInPayload() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(request.url?.absoluteString, "https://pda.test/api/community/feedback/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let obj = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as! [String: Any]
            XCTAssertEqual(
                Set(obj.keys),
                ["title", "description", "feedback_types", "metadata"]
            )
            let meta = obj["metadata"] as! [String: Any]
            XCTAssertEqual(Set(meta.keys), ["route", "user_agent", "app_version"])
            XCTAssertEqual(meta["app_version"] as? String, "")
            let body = try JSONDecoder().decode(FeedbackBody.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.title, "crash on events")
            XCTAssertEqual(body.description, "it explodes")
            XCTAssertEqual(body.feedbackTypes, ["bug"])
            XCTAssertEqual(body.metadata.route, "/calendar")
            XCTAssertEqual(body.metadata.userAgent, "ios-test-agent")
            return MockHTTP.json(201, ["html_url": "https://github.com/owner/repo/issues/123"])
        }
        let model = FeedbackModel(client: makeClient(tokens), route: "/calendar", userAgent: "ios-test-agent")
        model.open = true
        model.setTitle("  crash on events  ")
        model.setDescription("  it explodes  ")
        model.bug = true
        await model.submit()
        XCTAssertEqual(model.toast, "feedback submitted — thanks! 🌱")
        XCTAssertEqual(model.issueURL?.absoluteString, "https://github.com/owner/repo/issues/123")
        XCTAssertEqual(model.issueLabel, "view your issue")
        XCTAssertFalse(model.open)
        XCTAssertNil(model.titleError)
        XCTAssertNil(model.descriptionError)
    }

    func test_submitFeedback_ordersSelectedTypes() async throws {
        MockHTTP.handler = { request in
            let body = try JSONDecoder().decode(FeedbackBody.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.feedbackTypes, ["bug", "feature request", "improvement"])
            return MockHTTP.json(201, ["html_url": "https://example.com/1"])
        }
        let model = FeedbackModel(client: makeClient(MemoryTokenStore()), route: "/calendar", userAgent: "ios")
        model.setTitle("t")
        model.setDescription("d")
        model.improvement = true
        model.bug = true
        model.feature = true
        await model.submit()
        XCTAssertEqual(model.toast, FeedbackCopy.saved)
    }

    func test_submitFeedback_requiresTitleAndDescription() async {
        var posts = 0
        MockHTTP.handler = { _ in
            posts += 1
            return MockHTTP.json(201, ["html_url": "https://example.com/1"])
        }
        let model = FeedbackModel(client: makeClient(), route: "/calendar", userAgent: "ios")
        model.open = true
        await model.submit()
        XCTAssertEqual(posts, 0)
        XCTAssertEqual(model.titleError, "required")
        XCTAssertEqual(model.descriptionError, "required")
        XCTAssertTrue(model.open)
        model.setTitle("   ")
        model.setDescription("kept")
        await model.submit()
        XCTAssertEqual(posts, 0)
        XCTAssertEqual(model.titleError, "required")
        XCTAssertNil(model.descriptionError)
    }

    func test_submitFeedback_clampsFieldLength() {
        let model = FeedbackModel(client: makeClient(), route: "/calendar", userAgent: "ios")
        model.setTitle(String(repeating: "a", count: 180))
        model.setDescription(String(repeating: "b", count: 2100))
        XCTAssertEqual(model.title.count, 150)
        XCTAssertEqual(model.description.count, 2000)
    }

    func test_submitFeedback_forbiddenKeepsFormOpen() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = FeedbackModel(client: makeClient(tokens), route: "/calendar", userAgent: "ios")
        model.open = true
        model.setTitle("t")
        model.setDescription("d")
        await model.submit()
        XCTAssertEqual(model.toast, "couldn't submit feedback — try again")
        XCTAssertTrue(model.open)
        XCTAssertNil(model.issueURL)
        XCTAssertEqual(model.submitLabel, "submit")
    }

    func test_submitFeedback_withoutIssueURL() async {
        MockHTTP.handler = { _ in MockHTTP.json(201, ["html_url": ""]) }
        let model = FeedbackModel(client: makeClient(), route: "/calendar", userAgent: "ios")
        model.open = true
        model.setTitle("t")
        model.setDescription("d")
        await model.submit()
        XCTAssertEqual(model.toast, FeedbackCopy.saved)
        XCTAssertNil(model.issueURL)
        XCTAssertFalse(model.open)
    }

    func test_cancelFeedback_clearsWithoutPosting() async {
        var posts = 0
        MockHTTP.handler = { _ in
            posts += 1
            return MockHTTP.json(500, [:])
        }
        let model = FeedbackModel(client: makeClient(), route: "/calendar", userAgent: "ios")
        model.open = true
        model.setTitle("t")
        model.setDescription("d")
        model.bug = true
        model.titleError = "required"
        model.cancel()
        XCTAssertEqual(posts, 0)
        XCTAssertFalse(model.open)
        XCTAssertEqual(model.title, "")
        XCTAssertEqual(model.description, "")
        XCTAssertFalse(model.bug)
        XCTAssertNil(model.titleError)
    }

    func test_feedbackCopy_isLowercase() {
        let lines = [
            FeedbackCopy.button,
            FeedbackCopy.mark,
            FeedbackCopy.title,
            FeedbackCopy.description,
            FeedbackCopy.bug,
            FeedbackCopy.feature,
            FeedbackCopy.improvement,
            FeedbackCopy.cancel,
            FeedbackCopy.submit,
            FeedbackCopy.sending,
            FeedbackCopy.required,
            FeedbackCopy.saved,
            FeedbackCopy.viewIssue,
            FeedbackCopy.failed,
        ]
        XCTAssertEqual(lines, lines.map { $0.lowercased() })
        XCTAssertEqual(FeedbackCopy.button, "send feedback")
        XCTAssertEqual(FeedbackCopy.mark, "?")
        XCTAssertEqual(FeedbackCopy.sending, "sending...")
        XCTAssertEqual(FeedbackCopy.saved, "feedback submitted — thanks! 🌱")
        XCTAssertEqual(FeedbackCopy.viewIssue, "view your issue")
        XCTAssertEqual(FeedbackCopy.failed, "couldn't submit feedback — try again")
    }

    private func user() throws -> SessionUser {
        try Event.decoder.decode(
            SessionUser.self,
            from: Data(#"{"id":"user-1","first_name":"ada","email":"ada@pda.test"}"#.utf8)
        )
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private struct FeedbackBody: Decodable {
    let title: String
    let description: String
    let feedbackTypes: [String]
    let metadata: FeedbackMeta

    enum CodingKeys: String, CodingKey {
        case title, description
        case feedbackTypes = "feedback_types"
        case metadata
    }
}

private struct FeedbackMeta: Decodable {
    let route: String
    let userAgent: String
    let appVersion: String

    enum CodingKeys: String, CodingKey {
        case route
        case userAgent = "user_agent"
        case appVersion = "app_version"
    }
}
