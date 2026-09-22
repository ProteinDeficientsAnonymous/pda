import XCTest

@testable import PDA

final class AddQuestionTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_addQuestionURL_keepsTrailingSlash() {
        let url = addQuestionURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/join-form/questions/")
        XCTAssertNil(url.query)
    }

    func test_joinQuestionTypes_matchWeb() {
        XCTAssertEqual(joinQuestionTypeChoices.map(\.value), ["text", "textarea", "select"])
        XCTAssertEqual(joinQuestionTypeChoices.map(\.label), ["short text", "short answer", "select"])
        XCTAssertEqual(joinQuestionOptions([" vegan ", "  ", "other"]), ["vegan", "other"])
        XCTAssertEqual(joinQuestionPayloadOptions(fieldType: "text", options: ["kept"]), [])
        XCTAssertEqual(joinQuestionPayloadOptions(fieldType: "textarea", options: ["kept"]), [])
        XCTAssertEqual(
            joinQuestionPayloadOptions(fieldType: "select", options: [" vegan ", ""]),
            ["vegan"]
        )
    }

    func test_addQuestion_postsTrimmedTextQuestion() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/join-form/questions/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try payload(request.httpBody ?? Data())
            XCTAssertEqual(body.label, "why join")
            XCTAssertEqual(body.fieldType, "text")
            XCTAssertEqual(body.options, [])
            XCTAssertEqual(body.required, true)
            return MockHTTP.json(201, questionJSON(id: "q2", label: "why join", type: "text", order: 1, required: true))
        }
        let form = AdminJoinFormModel(client: makeClient(tokens))
        form.questions = [
            JoinQuestion(id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0),
        ]
        let model = AddQuestionModel(client: makeClient(tokens))
        XCTAssertEqual(model.fieldType, "text")
        XCTAssertFalse(model.showsOptions)
        model.label = "  why join  "
        model.required = true
        let saved = await model.save()
        XCTAssertTrue(saved)
        XCTAssertTrue(model.closed)
        let created = try XCTUnwrap(model.created)
        form.includeCreated(created)
        XCTAssertEqual(form.questions.map(\.id), ["q1", "q2"])
        XCTAssertEqual(form.questions[1].label, "why join")
        XCTAssertEqual(model.saveLabel, AddQuestionCopy.save)
    }

    func test_addQuestion_postsSelectWithoutBlankOptions() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            let body = try payload(request.httpBody ?? Data())
            XCTAssertEqual(body.fieldType, "select")
            XCTAssertEqual(body.options, ["vegan", "other"])
            XCTAssertEqual(body.required, false)
            return MockHTTP.json(201, questionJSON(
                id: "q2",
                label: "diet",
                type: "select",
                order: 1,
                options: ["vegan", "other"]
            ))
        }
        let model = AddQuestionModel(client: makeClient(tokens))
        model.label = "diet"
        model.fieldType = "select"
        XCTAssertTrue(model.showsOptions)
        model.options = [" vegan ", "  ", "other"]
        let saved = await model.save()
        XCTAssertTrue(saved)
        XCTAssertEqual(model.created?.options, ["vegan", "other"])
    }

    func test_addQuestion_emptyLabelDoesNotPost() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(201, questionJSON(id: "q", label: "x", type: "text", order: 0))
        }
        let model = AddQuestionModel(client: makeClient())
        model.label = "   "
        model.fieldType = "select"
        model.options = []
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(called)
        XCTAssertEqual(model.formError, "label required")
        XCTAssertFalse(model.closed)
        XCTAssertNil(model.created)
    }

    func test_addQuestion_selectWithoutOptionsDoesNotPost() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(201, questionJSON(id: "q", label: "x", type: "select", order: 0))
        }
        let model = AddQuestionModel(client: makeClient())
        model.label = "diet"
        model.fieldType = "select"
        model.options = ["  ", ""]
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(called)
        XCTAssertEqual(model.formError, "add at least one option")
    }

    func test_addQuestion_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AddQuestionModel(client: makeClient())
        model.label = "diet"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.created)
        XCTAssertEqual(model.explanationTitle, "add question")
        XCTAssertEqual(
            model.explanationBody,
            "you need permission to edit join questions to add a question."
        )
    }

    func test_addQuestion_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = AddQuestionModel(client: makeClient())
        model.label = "diet"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(model.forbidden)
        XCTAssertEqual(model.formError, "couldn't save — try again")
        XCTAssertNil(model.created)
    }

    func test_addQuestion_cancelDoesNotPost() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(201, questionJSON(id: "q", label: "x", type: "text", order: 0))
        }
        let model = AddQuestionModel(client: makeClient())
        model.label = "diet"
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertFalse(called)
        XCTAssertNil(model.created)
    }

    func test_addQuestion_pendingLabelIsSaving() {
        let model = AddQuestionModel(client: makeClient())
        XCTAssertEqual(model.saveLabel, "save")
        model.saving = true
        XCTAssertEqual(model.saveLabel, "saving…")
        XCTAssertFalse(model.canSave)
    }

    func test_addQuestionCopy_isLowercase() {
        XCTAssertEqual(AddQuestionCopy.button, "add question")
        XCTAssertEqual(AddQuestionCopy.title, "add question")
        XCTAssertEqual(AddQuestionCopy.labelRequired, "label required")
        XCTAssertEqual(AddQuestionCopy.optionsRequired, "add at least one option")
        XCTAssertEqual(AddQuestionCopy.failure, "couldn't save — try again")
        let blobs = [
            AddQuestionCopy.button,
            AddQuestionCopy.title,
            AddQuestionCopy.labelField,
            AddQuestionCopy.type,
            AddQuestionCopy.required,
            AddQuestionCopy.options,
            AddQuestionCopy.addOption,
            AddQuestionCopy.remove,
            AddQuestionCopy.save,
            AddQuestionCopy.saving,
            AddQuestionCopy.cancel,
            AddQuestionCopy.labelRequired,
            AddQuestionCopy.optionsRequired,
            AddQuestionCopy.failure,
            AddQuestionCopy.forbiddenTitle,
            AddQuestionCopy.forbiddenBody,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_editQuestion_prefillsAndPatchesAllFields() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        let existing = JoinQuestion(
            id: "q1",
            label: "Diet",
            fieldType: "select",
            required: true,
            options: ["vegan", "other"],
            displayOrder: 0
        )
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/join-form/questions/q1/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try payload(request.httpBody ?? Data())
            XCTAssertEqual(body.label, "diet")
            XCTAssertEqual(body.fieldType, "select")
            XCTAssertEqual(body.options, ["vegan"])
            XCTAssertEqual(body.required, true)
            return MockHTTP.json(200, questionJSON(
                id: "q1",
                label: "diet",
                type: "select",
                order: 0,
                required: true,
                options: ["vegan"]
            ))
        }
        let model = AddQuestionModel(client: makeClient(tokens), question: existing)
        XCTAssertEqual(model.title, "edit question")
        XCTAssertEqual(model.label, "Diet")
        XCTAssertEqual(model.fieldType, "select")
        XCTAssertEqual(model.required, true)
        XCTAssertEqual(model.options, ["vegan", "other"])
        XCTAssertTrue(model.showsOptions)
        model.label = "  diet  "
        model.options = [" vegan ", ""]
        let saved = await model.save()
        XCTAssertTrue(saved)
        XCTAssertTrue(model.closed)
        let updated = try XCTUnwrap(model.created)
        let form = AdminJoinFormModel(client: makeClient(tokens))
        form.questions = [
            existing,
            JoinQuestion(id: "q2", label: "Why", fieldType: "text", required: false, options: [], displayOrder: 1),
        ]
        form.replaceUpdated(updated)
        XCTAssertEqual(form.questions.map(\.id), ["q1", "q2"])
        XCTAssertEqual(form.questions[0].label, "diet")
        XCTAssertEqual(form.questions[0].options, ["vegan"])
    }

    func test_editQuestion_textSendsEmptyOptions() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            let body = try payload(request.httpBody ?? Data())
            XCTAssertEqual(body.fieldType, "textarea")
            XCTAssertEqual(body.options, [])
            XCTAssertEqual(body.required, false)
            return MockHTTP.json(200, questionJSON(id: "q1", label: "why", type: "textarea", order: 0))
        }
        let existing = JoinQuestion(
            id: "q1",
            label: "Diet",
            fieldType: "select",
            required: true,
            options: ["vegan"],
            displayOrder: 0
        )
        let model = AddQuestionModel(client: makeClient(), question: existing)
        model.label = "why"
        model.fieldType = "textarea"
        model.required = false
        XCTAssertFalse(model.showsOptions)
        let saved = await model.save()
        XCTAssertTrue(saved)
    }

    func test_editQuestion_emptyLabelDoesNotPatch() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, questionJSON(id: "q1", label: "x", type: "text", order: 0))
        }
        let existing = JoinQuestion(
            id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0
        )
        let model = AddQuestionModel(client: makeClient(), question: existing)
        model.label = "   "
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(called)
        XCTAssertEqual(model.formError, "label required")
        XCTAssertFalse(model.closed)
    }

    func test_editQuestion_selectWithoutOptionsDoesNotPatch() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, questionJSON(id: "q1", label: "diet", type: "select", order: 0))
        }
        let existing = JoinQuestion(
            id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0
        )
        let model = AddQuestionModel(client: makeClient(), question: existing)
        model.fieldType = "select"
        model.options = ["  ", ""]
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(called)
        XCTAssertEqual(model.formError, "add at least one option")
    }

    func test_editQuestion_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let existing = JoinQuestion(
            id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0
        )
        let model = AddQuestionModel(client: makeClient(), question: existing)
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.created)
        XCTAssertEqual(model.explanationTitle, "edit question")
        XCTAssertEqual(
            model.explanationBody,
            "you need permission to edit join questions to edit this question."
        )
    }

    func test_editQuestion_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let existing = JoinQuestion(
            id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0
        )
        let model = AddQuestionModel(client: makeClient(), question: existing)
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(model.forbidden)
        XCTAssertEqual(model.formError, "couldn't save — try again")
    }

    func test_editQuestion_cancelDoesNotPatch() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, questionJSON(id: "q1", label: "Diet", type: "text", order: 0))
        }
        let existing = JoinQuestion(
            id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0
        )
        let model = AddQuestionModel(client: makeClient(), question: existing)
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertFalse(called)
        XCTAssertNil(model.created)
    }

    func test_editQuestionCopy_isLowercase() {
        XCTAssertEqual(AddQuestionCopy.edit, "edit")
        XCTAssertEqual(AddQuestionCopy.editTitle, "edit question")
        XCTAssertEqual(
            updateJoinQuestionURL(base: base, id: "q1").absoluteString,
            "https://pda.test/api/community/join-form/questions/q1/"
        )
        let blobs = [
            AddQuestionCopy.edit,
            AddQuestionCopy.editTitle,
            AddQuestionCopy.editForbiddenBody,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private struct AddQuestionPayload: Decodable {
    let label: String
    let fieldType: String
    let options: [String]
    let required: Bool

    enum CodingKeys: String, CodingKey {
        case label, options, required
        case fieldType = "field_type"
    }
}

private func payload(_ data: Data) throws -> AddQuestionPayload {
    try JSONDecoder().decode(AddQuestionPayload.self, from: data)
}

private func questionJSON(
    id: String,
    label: String,
    type: String,
    order: Int,
    required: Bool = false,
    options: [String] = []
) -> [String: Any] {
    [
        "id": id,
        "label": label,
        "field_type": type,
        "options": options,
        "required": required,
        "display_order": order,
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
