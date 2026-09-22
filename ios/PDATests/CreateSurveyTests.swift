import XCTest

@testable import PDA

final class CreateSurveyTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_createSurvey_postsWebBodyWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let posted = try JSONDecoder().decode(PostedSurvey.self, from: request.httpBody ?? Data())
            XCTAssertEqual(posted.title, "retreat a")
            XCTAssertEqual(posted.description, "tell us things")
            XCTAssertEqual(posted.slug, "retreat-a")
            XCTAssertEqual(posted.visibility, "members_only")
            XCTAssertTrue(posted.isActive)
            XCTAssertFalse(posted.oneResponsePerUser)
            XCTAssertEqual(posted.linkedEventId, "evt-1")
            return MockHTTP.json(201, ["id": "s-new"])
        }
        var input = CreateSurveyInput.empty
        input.title = "retreat a"
        input.description = "tell us things"
        input.slug = "retreat-a"
        input.linkedEventId = "evt-1"
        let created = try await makeClient(tokens).createSurvey(input)
        XCTAssertEqual(created.id, "s-new")
    }

    func test_createSurvey_blankTitleOrSlugDoesNotPost() async {
        MockHTTP.handler = { _ in
            XCTFail("blank survey should not post")
            return MockHTTP.json(500, [:])
        }
        let model = CreateSurveyModel(client: makeClient())
        await model.submit()
        XCTAssertEqual(model.banner, "title and slug are required")
        XCTAssertNil(model.createdID)

        model.input.title = "   "
        model.input.slug = "retreat-a"
        await model.submit()
        XCTAssertEqual(model.banner, "title and slug are required")
        XCTAssertNil(model.createdID)
    }

    func test_createSurvey_403IsThePermissionGate() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "manage_surveys"]]])
        }
        let model = filledModel()
        await model.submit()
        XCTAssertNil(model.createdID)
        XCTAssertNil(model.slugError)
        XCTAssertEqual(model.banner, "you don't have permission to do that")
    }

    func test_createSurvey_slugAndLinkedEventStayOnTheField() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(400, ["detail": [["code": "survey.slug_already_exists", "field": "slug"]]])
        }
        let model = filledModel()
        await model.submit()
        XCTAssertEqual(model.slugError, "a survey with that slug already exists")
        XCTAssertNil(model.banner)
        XCTAssertNil(model.createdID)

        model.setSlug("retreat-a-2")
        XCTAssertNil(model.slugError)

        MockHTTP.handler = { _ in
            MockHTTP.json(400, ["detail": [["code": "event.not_found", "field": "linked_event_id"]]])
        }
        await model.submit()
        XCTAssertEqual(model.linkedEventError, "event not found")
        XCTAssertNil(model.banner)
        XCTAssertNil(model.slugError)

        model.setLinkedEvent(nil)
        XCTAssertNil(model.linkedEventError)
    }

    func test_createSurvey_otherFailureUsesTheBanner() async {
        MockHTTP.handler = { _ in MockHTTP.json(500, ["detail": "nope"]) }
        let model = filledModel()
        await model.submit()
        XCTAssertEqual(model.banner, "couldn't complete that action — try again")
        XCTAssertNil(model.slugError)
        XCTAssertNil(model.linkedEventError)
        XCTAssertNil(model.createdID)
    }

    func test_createSurveyCopyAndEventLabel_areLowercase() {
        let start = Event.parseISODate("2026-03-01T00:00:00Z")
        XCTAssertEqual(
            surveyLinkedEventLabel(title: "Potluck", start: start),
            "potluck · mar 1, 2026"
        )
        XCTAssertEqual(
            surveyEventOptions(
                events: [],
                selectedID: "evt-gone"
            ),
            [SurveyEventOption(id: "evt-gone", label: "current linked event")]
        )
        XCTAssertEqual(clampedSurveyTitle(String(repeating: "a", count: 201)).count, 200)
        XCTAssertEqual(clampedSurveySlug(String(repeating: "b", count: 101)).count, 100)
        XCTAssertEqual(clampedSurveyDescription(String(repeating: "c", count: 2001)).count, 2000)
        let blobs = [
            CreateSurveyCopy.button,
            CreateSurveyCopy.title,
            CreateSurveyCopy.titleLabel,
            CreateSurveyCopy.slugLabel,
            CreateSurveyCopy.slugHint,
            CreateSurveyCopy.descriptionLabel,
            CreateSurveyCopy.visibilityLabel,
            CreateSurveyCopy.membersOnly,
            CreateSurveyCopy.publicVisibility,
            CreateSurveyCopy.linkedEvent,
            CreateSurveyCopy.none,
            CreateSurveyCopy.currentLinked,
            CreateSurveyCopy.oneResponse,
            CreateSurveyCopy.cancel,
            CreateSurveyCopy.create,
            CreateSurveyCopy.creating,
            CreateSurveyCopy.required,
            CreateSurveyCopy.slugTaken,
            CreateSurveyCopy.eventNotFound,
            CreateSurveyCopy.failure,
            CreateSurveyCopy.forbidden,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
        XCTAssertEqual(CreateSurveyInput.empty.visibility, "members_only")
        XCTAssertTrue(CreateSurveyInput.empty.isActive)
        XCTAssertFalse(CreateSurveyInput.empty.oneResponsePerUser)
        XCTAssertNil(CreateSurveyInput.empty.linkedEventId)
    }

    private func filledModel() -> CreateSurveyModel {
        let model = CreateSurveyModel(client: makeClient())
        model.input.title = "retreat a"
        model.input.slug = "retreat-a"
        model.input.linkedEventId = "evt-1"
        return model
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private struct PostedSurvey: Decodable {
    let title: String
    let description: String
    let slug: String
    let visibility: String
    let isActive: Bool
    let oneResponsePerUser: Bool
    let linkedEventId: String?

    private enum CodingKeys: String, CodingKey {
        case title, description, slug, visibility
        case isActive = "is_active"
        case oneResponsePerUser = "one_response_per_user"
        case linkedEventId = "linked_event_id"
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
