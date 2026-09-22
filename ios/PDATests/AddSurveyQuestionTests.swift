import XCTest

@testable import PDA

final class AddSurveyQuestionTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_createSurveyQuestion_postsWebBodyWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/srv-1/questions/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let posted = try JSONDecoder().decode(PostedQuestion.self, from: request.httpBody ?? Data())
            XCTAssertEqual(posted.label, "Meal")
            XCTAssertEqual(posted.fieldType, "text")
            XCTAssertEqual(posted.options, [])
            XCTAssertFalse(posted.required)
            return MockHTTP.json(201, questionJSON())
        }
        let created = try await makeClient(tokens).createSurveyQuestion(
            surveyId: "srv-1",
            label: "Meal",
            fieldType: "text",
            options: [],
            required: false
        )
        XCTAssertEqual(created.id, "q1")
        XCTAssertEqual(created.label, "Meal")
    }

    func test_addSurveyQuestion_blankLabelDoesNotPost() async {
        MockHTTP.handler = { _ in
            XCTFail("blank label should not post")
            return MockHTTP.json(500, [:])
        }
        let model = AddSurveyQuestionModel(client: makeClient(), surveyId: "srv-1")
        model.label = "   "
        await model.save()
        XCTAssertEqual(model.banner, "label required")
        XCTAssertNil(model.created)
    }

    func test_addSurveyQuestion_requiresOptionsThenPostsTrimmed() async {
        MockHTTP.handler = { _ in
            XCTFail("empty options should not post")
            return MockHTTP.json(500, [:])
        }
        let model = AddSurveyQuestionModel(client: makeClient(), surveyId: "srv-1")
        model.label = " Meal "
        model.fieldType = "select"
        model.required = true
        await model.save()
        XCTAssertEqual(model.banner, "add at least one option")
        XCTAssertNil(model.created)

        MockHTTP.handler = { request in
            let posted = try JSONDecoder().decode(PostedQuestion.self, from: request.httpBody ?? Data())
            XCTAssertEqual(posted.label, "Meal")
            XCTAssertEqual(posted.fieldType, "select")
            XCTAssertEqual(posted.options, ["vegan", "omni"])
            XCTAssertTrue(posted.required)
            return MockHTTP.json(201, questionJSON(type: "select", options: ["vegan", "omni"], required: true))
        }
        model.options = [" vegan ", "", "omni"]
        await model.save()
        XCTAssertEqual(model.created?.id, "q1")
        XCTAssertNil(model.banner)
    }

    func test_addSurveyQuestion_403IsThePermissionGate() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "manage_surveys"]]])
        }
        let model = filledModel()
        await model.save()
        XCTAssertNil(model.created)
        XCTAssertEqual(model.banner, "you don't have permission to do that")
    }

    func test_addSurveyQuestion_missingSurveyAndOtherFailure() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(404, ["detail": [["code": "survey.not_found"]]])
        }
        let missing = filledModel()
        await missing.save()
        XCTAssertEqual(missing.banner, "survey not found")
        XCTAssertNil(missing.created)

        MockHTTP.handler = { _ in MockHTTP.json(500, ["detail": "nope"]) }
        let failed = filledModel()
        await failed.save()
        XCTAssertEqual(failed.banner, "couldn't save — try again")
        XCTAssertNil(failed.created)
    }

    func test_surveyQuestions_loadsExistingSurvey() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/srv-1/admin/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "id": "srv-1",
                "title": "Retreat",
                "slug": "retreat-a",
                "visibility": "members_only",
                "questions": [questionJSON(label: "Meal", type: "select", options: ["vegan"], required: true)],
            ])
        }
        let model = SurveyQuestionsModel(client: makeClient(tokens), surveyId: "srv-1")
        await model.load()
        let question = try XCTUnwrap(model.survey?.questions.first)
        XCTAssertEqual(adminSurveyQuestionLabel(question), "meal · required")
        XCTAssertEqual(adminSurveyQuestionMeta(question), "select · 1 options")
        XCTAssertNil(model.error)
    }

    func test_addSurveyQuestionCopy_matchesWebAndIsLowercase() {
        XCTAssertEqual(
            surveyQuestionTypeChoices.map(\.value),
            ["text", "textarea", "radio", "select", "checkbox", "number", "boolean", "rating", "datetime_poll"]
        )
        XCTAssertEqual(surveyQuestionTypeChoices.map(\.label), surveyQuestionTypeChoices.map(\.label).map { $0.lowercased() })
        XCTAssertFalse(surveyQuestionWantsOptions("text"))
        XCTAssertTrue(surveyQuestionWantsOptions("select"))
        XCTAssertTrue(surveyQuestionWantsOptions("rating"))
        XCTAssertTrue(surveyQuestionWantsOptions("datetime_poll"))
        XCTAssertEqual(surveyQuestionOptionsHint("rating"), "up to 5 star labels")
        XCTAssertEqual(surveyQuestionOptionsHint("datetime_poll"), "iso-8601 datetime values")
        XCTAssertNil(surveyQuestionOptionsHint("text"))
        XCTAssertEqual(clampedSurveyQuestionLabel(String(repeating: "a", count: 201)).count, 200)
        let model = AddSurveyQuestionModel(client: makeClient(), surveyId: "srv-1")
        XCTAssertEqual(model.fieldType, "text")
        XCTAssertFalse(model.required)
        model.options = ["  "]
        model.setFieldType("radio")
        XCTAssertEqual(model.options, [""])
        let blobs = [
            AddSurveyQuestionCopy.button,
            AddSurveyQuestionCopy.title,
            AddSurveyQuestionCopy.questions,
            AddSurveyQuestionCopy.empty,
            AddSurveyQuestionCopy.loadError,
            AddSurveyQuestionCopy.label,
            AddSurveyQuestionCopy.type,
            AddSurveyQuestionCopy.options,
            AddSurveyQuestionCopy.addOption,
            AddSurveyQuestionCopy.remove,
            AddSurveyQuestionCopy.required,
            AddSurveyQuestionCopy.cancel,
            AddSurveyQuestionCopy.save,
            AddSurveyQuestionCopy.saving,
            AddSurveyQuestionCopy.labelRequired,
            AddSurveyQuestionCopy.optionsRequired,
            AddSurveyQuestionCopy.failure,
            AddSurveyQuestionCopy.forbidden,
            AddSurveyQuestionCopy.notFound,
            AddSurveyQuestionCopy.ratingHint,
            AddSurveyQuestionCopy.pollHint,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_updateSurveyQuestion_patchesEveryFieldWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/srv-1/questions/q1/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let posted = try JSONDecoder().decode(PostedQuestion.self, from: request.httpBody ?? Data())
            XCTAssertEqual(posted.label, "Meal")
            XCTAssertEqual(posted.fieldType, "select")
            XCTAssertEqual(posted.options, ["vegan", "omni"])
            XCTAssertTrue(posted.required)
            return MockHTTP.json(200, questionJSON(type: "select", options: ["vegan", "omni"], required: true))
        }
        let updated = try await makeClient(tokens).updateSurveyQuestion(
            surveyId: "srv-1",
            questionId: "q1",
            label: "Meal",
            fieldType: "select",
            options: ["vegan", "omni"],
            required: true
        )
        XCTAssertEqual(updated.id, "q1")
        XCTAssertEqual(updated.fieldType, "select")
    }

    func test_editSurveyQuestion_startsFromExistingAndValidates() async {
        MockHTTP.handler = { _ in
            XCTFail("invalid edit should not patch")
            return MockHTTP.json(500, [:])
        }
        let existing = PublicSurveyQuestion(
            id: "q1",
            label: "Meal",
            fieldType: "select",
            options: ["vegan"],
            required: true,
            displayOrder: 0
        )
        let model = AddSurveyQuestionModel(client: makeClient(), surveyId: "srv-1", question: existing)
        XCTAssertEqual(model.title, "edit question")
        XCTAssertEqual(model.label, "Meal")
        XCTAssertEqual(model.fieldType, "select")
        XCTAssertEqual(model.options, ["vegan"])
        XCTAssertTrue(model.required)

        model.label = "   "
        await model.save()
        XCTAssertEqual(model.banner, "label required")
        XCTAssertNil(model.created)

        model.label = "Meal"
        model.options = ["  "]
        await model.save()
        XCTAssertEqual(model.banner, "add at least one option")
        XCTAssertNil(model.created)
    }

    func test_editSurveyQuestion_textSaveStillSendsOptions() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            let posted = try JSONDecoder().decode(PostedQuestion.self, from: request.httpBody ?? Data())
            XCTAssertEqual(posted.label, "Meal")
            XCTAssertEqual(posted.fieldType, "text")
            XCTAssertEqual(posted.options, [])
            XCTAssertTrue(posted.required)
            return MockHTTP.json(200, questionJSON(required: true))
        }
        let existing = PublicSurveyQuestion(
            id: "q1",
            label: "Meal",
            fieldType: "select",
            options: ["vegan"],
            required: true,
            displayOrder: 0
        )
        let model = AddSurveyQuestionModel(client: makeClient(), surveyId: "srv-1", question: existing)
        model.setFieldType("text")
        await model.save()
        XCTAssertEqual(model.created?.fieldType, "text")
        XCTAssertNil(model.banner)
    }

    func test_editSurveyQuestion_403IsThePermissionGate() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "manage_surveys"]]])
        }
        let model = editModel()
        await model.save()
        XCTAssertNil(model.created)
        XCTAssertEqual(model.banner, "you don't have permission to do that")
    }

    func test_editSurveyQuestion_missingQuestionUsesBanner() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(404, ["detail": [["code": "survey.question_not_found"]]])
        }
        let model = editModel()
        await model.save()
        XCTAssertNil(model.created)
        XCTAssertEqual(model.banner, "question not found")
        XCTAssertEqual(AddSurveyQuestionCopy.edit, "edit")
        XCTAssertEqual(AddSurveyQuestionCopy.editTitle, "edit question")
        XCTAssertEqual(AddSurveyQuestionCopy.questionNotFound, AddSurveyQuestionCopy.questionNotFound.lowercased())
    }

    func test_deleteSurveyQuestion_sendsDeleteWithBearerThenReloads() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "DELETE" {
                XCTAssertEqual(routePath(request.url), "/api/community/surveys/srv-1/questions/q1/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                return (204, Data(), [:])
            }
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/srv-1/admin/")
            return MockHTTP.json(200, [
                "id": "srv-1",
                "title": "Retreat",
                "slug": "retreat-a",
                "visibility": "members_only",
                "questions": [],
            ])
        }
        let model = SurveyQuestionsModel(client: makeClient(tokens), surveyId: "srv-1")
        model.pendingDelete = mealQuestion()
        await model.commitDelete()
        XCTAssertNil(model.actionError)
        XCTAssertEqual(model.survey?.questions.count, 0)
        XCTAssertNil(model.pendingDelete)
    }

    func test_deleteSurveyQuestion_403IsThePermissionGate() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "DELETE")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "manage_surveys"]]])
        }
        let model = SurveyQuestionsModel(client: makeClient(), surveyId: "srv-1")
        model.pendingDelete = mealQuestion()
        await model.commitDelete()
        XCTAssertEqual(model.actionError, "you don't have permission to do that")
        XCTAssertNil(model.survey)
        XCTAssertNil(model.error)
    }

    func test_surveyQuestionDeleteMessage_matchesWebConfirm() {
        XCTAssertEqual(
            surveyQuestionDeleteMessage("Meal"),
            "delete \"Meal\"? this also deletes responses to it."
        )
        XCTAssertEqual(DeleteSurveyQuestionCopy.title, "delete question")
        XCTAssertEqual(DeleteSurveyQuestionCopy.confirm, "delete")
        XCTAssertEqual(DeleteSurveyQuestionCopy.cancel, "cancel")
        for text in [DeleteSurveyQuestionCopy.title, DeleteSurveyQuestionCopy.confirm, DeleteSurveyQuestionCopy.cancel] {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_deleteSurveyQuestion_cancelDoesNotSend() {
        MockHTTP.handler = { _ in
            XCTFail("cancel should not delete")
            return MockHTTP.json(500, [:])
        }
        let model = SurveyQuestionsModel(client: makeClient(), surveyId: "srv-1")
        model.pendingDelete = mealQuestion()
        model.cancelDelete()
        XCTAssertNil(model.pendingDelete)
    }

    func test_reorderSurveyQuestions_moveDownPutsWebBodyWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PUT")
            XCTAssertEqual(routePath(request.url), "/api/community/surveys/srv-1/questions/order/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONDecoder().decode(SurveyOrderPayload.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.questionIds, ["q2", "q1"])
            return MockHTTP.json(200, [
                questionJSON(id: "q2", label: "second", displayOrder: 0),
                questionJSON(id: "q1", label: "first", displayOrder: 1),
            ])
        }
        let model = try loadedQuestions(ids: ["q1", "q2"], tokens: tokens)
        await model.moveDown(at: 0)
        XCTAssertEqual(model.survey?.questions.map(\.id), ["q2", "q1"])
        XCTAssertNil(model.actionError)
    }

    func test_reorderSurveyQuestions_moveUpPutsSwappedIds() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PUT")
            let body = try JSONDecoder().decode(SurveyOrderPayload.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.questionIds, ["q2", "q1"])
            return MockHTTP.json(200, [
                questionJSON(id: "q2", label: "second", displayOrder: 0),
                questionJSON(id: "q1", label: "first", displayOrder: 1),
            ])
        }
        let model = try loadedQuestions(ids: ["q1", "q2"])
        await model.moveUp(at: 1)
        XCTAssertEqual(model.survey?.questions.map(\.id), ["q2", "q1"])
    }

    func test_surveyQuestionMoveButtons_skipEnds() {
        XCTAssertFalse(showsSurveyQuestionMoveUp(index: 0, count: 2))
        XCTAssertTrue(showsSurveyQuestionMoveDown(index: 0, count: 2))
        XCTAssertTrue(showsSurveyQuestionMoveUp(index: 1, count: 2))
        XCTAssertFalse(showsSurveyQuestionMoveDown(index: 1, count: 2))
        XCTAssertFalse(showsSurveyQuestionMoveUp(index: 0, count: 1))
        XCTAssertFalse(showsSurveyQuestionMoveDown(index: 0, count: 1))
        XCTAssertEqual(ReorderSurveyQuestionsCopy.moveUp, "move up")
        XCTAssertEqual(ReorderSurveyQuestionsCopy.moveDown, "move down")
        XCTAssertEqual(ReorderSurveyQuestionsCopy.moveUp, ReorderSurveyQuestionsCopy.moveUp.lowercased())
        XCTAssertEqual(ReorderSurveyQuestionsCopy.moveDown, ReorderSurveyQuestionsCopy.moveDown.lowercased())
        let url = reorderSurveyQuestionsURL(base: base, surveyId: "srv-1")
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/surveys/srv-1/questions/order/")
        XCTAssertNil(url.query)
    }

    func test_reorderSurveyQuestions_403LeavesOrder() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PUT")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "manage_surveys"]]])
        }
        let model = try loadedQuestions(ids: ["q1", "q2"])
        await model.moveDown(at: 0)
        XCTAssertEqual(model.actionError, "you don't have permission to do that")
        XCTAssertEqual(model.survey?.questions.map(\.id), ["q1", "q2"])
        XCTAssertNil(model.error)
    }

    func test_reorderSurveyQuestions_endsDoNotSend() async throws {
        MockHTTP.handler = { _ in
            XCTFail("ends should not reorder")
            return MockHTTP.json(500, [:])
        }
        let pair = try loadedQuestions(ids: ["q1", "q2"])
        await pair.moveUp(at: 0)
        await pair.moveDown(at: 1)
        XCTAssertEqual(pair.survey?.questions.map(\.id), ["q1", "q2"])
        let single = try loadedQuestions(ids: ["q1"])
        await single.moveUp(at: 0)
        await single.moveDown(at: 0)
        XCTAssertEqual(single.survey?.questions.map(\.id), ["q1"])
        XCTAssertNil(pair.actionError)
    }

    private func mealQuestion() -> PublicSurveyQuestion {
        PublicSurveyQuestion(
            id: "q1",
            label: "Meal",
            fieldType: "select",
            options: ["vegan"],
            required: true,
            displayOrder: 0
        )
    }

    private func editModel() -> AddSurveyQuestionModel {
        AddSurveyQuestionModel(
            client: makeClient(),
            surveyId: "srv-1",
            question: PublicSurveyQuestion(
                id: "q1",
                label: "Meal",
                fieldType: "text",
                options: [],
                required: false,
                displayOrder: 0
            )
        )
    }

    private func filledModel() -> AddSurveyQuestionModel {
        let model = AddSurveyQuestionModel(client: makeClient(), surveyId: "srv-1")
        model.label = "Meal"
        return model
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func loadedQuestions(ids: [String], tokens: MemoryTokenStore? = nil) throws -> SurveyQuestionsModel {
        let questions = ids.enumerated().map { index, id in
            questionJSON(id: id, label: id, displayOrder: index)
        }
        let data = try JSONSerialization.data(withJSONObject: [
            "id": "srv-1",
            "title": "Retreat",
            "slug": "retreat-a",
            "visibility": "members_only",
            "questions": questions,
        ])
        let model = SurveyQuestionsModel(client: makeClient(tokens), surveyId: "srv-1")
        model.survey = try JSONDecoder().decode(AdminSurveyDetail.self, from: data)
        return model
    }
}

private struct PostedQuestion: Decodable {
    let label: String
    let fieldType: String
    let options: [String]
    let required: Bool

    private enum CodingKeys: String, CodingKey {
        case label, options, required
        case fieldType = "field_type"
    }
}

private func questionJSON(
    id: String = "q1",
    label: String = "Meal",
    type: String = "text",
    options: [String] = [],
    required: Bool = false,
    displayOrder: Int = 0
) -> [String: Any] {
    [
        "id": id,
        "label": label,
        "field_type": type,
        "options": options,
        "required": required,
        "display_order": displayOrder,
    ]
}

private struct SurveyOrderPayload: Decodable {
    let questionIds: [String]

    enum CodingKeys: String, CodingKey {
        case questionIds = "question_ids"
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
