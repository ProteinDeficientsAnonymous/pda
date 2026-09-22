import XCTest

@testable import PDA

final class AdminJoinFormTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_adminJoinQuestionsURL_matchesWebList() {
        let url = adminJoinQuestionsURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/join-form/")
        XCTAssertNil(url.query)
    }

    func test_adminJoinQuestions_getsSortedListWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/join-form/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                questionJSON(id: "late", label: "Why", type: "text", order: 2),
                questionJSON(id: "early", label: "Diet", type: "select", order: 0, required: true, options: ["vegan", "other"]),
            ])
        }
        let rows = try await makeClient(tokens).adminJoinQuestions()
        XCTAssertEqual(rows.map(\.id), ["early", "late"])
        XCTAssertEqual(adminJoinQuestionTitle(rows[0]), "diet · required")
        XCTAssertEqual(adminJoinQuestionDetail(rows[0]), "select · 2 options")
        XCTAssertEqual(adminJoinQuestionTitle(rows[1]), "why")
        XCTAssertEqual(adminJoinQuestionDetail(rows[1]), "text")
    }

    func test_adminJoinQuestions_403WithoutEditPermission() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().adminJoinQuestions()
            XCTFail("403 should not return the questions")
        } catch AdminJoinFormError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminJoinFormModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminJoinFormModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.questions.isEmpty)
        XCTAssertEqual(model.explanationTitle, AdminJoinFormCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, AdminJoinFormCopy.forbiddenBody)
    }

    func test_joinFormTile_opensQuestionListOnly() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "edit_join_questions",
            "manage_documents",
        ]))
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .joinForm }.map(\.id), ["join-form"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .docs }.map(\.id), ["docs"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == nil }.map(\.id), [])
    }

    func test_adminJoinFormCopy_isLowercase() {
        let blobs = [
            AdminJoinFormCopy.title,
            AdminJoinFormCopy.subtitle,
            AdminJoinFormCopy.loading,
            AdminJoinFormCopy.error,
            AdminJoinFormCopy.empty,
            AdminJoinFormCopy.forbiddenTitle,
            AdminJoinFormCopy.forbiddenBody,
        ]
        XCTAssertEqual(AdminJoinFormCopy.title, "join form")
        XCTAssertEqual(AdminJoinFormCopy.error, "couldn't load questions — try refreshing")
        XCTAssertEqual(AdminJoinFormCopy.empty, "no custom questions yet")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_deleteQuestion_confirmsThenDeletes() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        let diet = JoinQuestion(id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0)
        let why = JoinQuestion(id: "q2", label: "why", fieldType: "textarea", required: false, options: [], displayOrder: 1)
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "DELETE")
            XCTAssertEqual(routePath(request.url), "/api/community/join-form/questions/q1/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            XCTAssertTrue(request.httpBody == nil || request.httpBody?.isEmpty == true)
            return MockHTTP.json(204, [:])
        }
        let model = AdminJoinFormModel(client: makeClient(tokens))
        model.questions = [diet, why]
        let prompt = model.prepareDelete(diet)
        XCTAssertEqual(prompt?.title, "delete question")
        XCTAssertEqual(prompt?.confirmLabel, "delete")
        XCTAssertEqual(prompt?.message, "delete \"Diet\"?")
        let deleted = await model.commitDelete()
        XCTAssertTrue(deleted)
        XCTAssertEqual(model.questions.map(\.id), ["q2"])
        XCTAssertNil(model.deleteError)
        XCTAssertFalse(model.deleteForbidden)
    }

    func test_deleteQuestion_cancelDoesNotCallAPI() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(204, [:])
        }
        let model = AdminJoinFormModel(client: makeClient())
        let diet = JoinQuestion(id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0)
        _ = model.prepareDelete(diet)
        model.cancelDelete()
        let deleted = await model.commitDelete()
        XCTAssertFalse(deleted)
        XCTAssertFalse(called)
        XCTAssertEqual(model.questions.map(\.id), [])
    }

    func test_deleteQuestion_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "DELETE")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let diet = JoinQuestion(id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0)
        let model = AdminJoinFormModel(client: makeClient())
        model.questions = [diet]
        _ = model.prepareDelete(diet)
        let deleted = await model.commitDelete()
        XCTAssertFalse(deleted)
        XCTAssertEqual(model.questions.map(\.id), ["q1"])
        XCTAssertTrue(model.deleteForbidden)
        XCTAssertEqual(model.deleteExplanationTitle, "delete question")
        XCTAssertEqual(
            model.deleteExplanationBody,
            "you need permission to edit join questions to delete this question."
        )
        XCTAssertNil(model.deleteError)
    }

    func test_deleteQuestion_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let diet = JoinQuestion(id: "q1", label: "Diet", fieldType: "text", required: false, options: [], displayOrder: 0)
        let model = AdminJoinFormModel(client: makeClient())
        model.questions = [diet]
        _ = model.prepareDelete(diet)
        let deleted = await model.commitDelete()
        XCTAssertFalse(deleted)
        XCTAssertEqual(model.questions.map(\.id), ["q1"])
        XCTAssertEqual(model.deleteError, "couldn't delete the question — try again")
        XCTAssertFalse(model.deleteForbidden)
    }

    func test_deleteQuestionCopy_isLowercase() {
        XCTAssertEqual(DeleteQuestionCopy.button, "delete")
        XCTAssertEqual(DeleteQuestionCopy.title, "delete question")
        XCTAssertEqual(DeleteQuestionCopy.confirm, "delete")
        XCTAssertEqual(DeleteQuestionCopy.failure, "couldn't delete the question — try again")
        let why = JoinQuestion(id: "q", label: "why", fieldType: "text", required: false, options: [], displayOrder: 0)
        XCTAssertEqual(joinQuestionDeleteMessage(why), "delete \"why\"?")
        let blobs = [
            DeleteQuestionCopy.button,
            DeleteQuestionCopy.title,
            DeleteQuestionCopy.confirm,
            DeleteQuestionCopy.cancel,
            DeleteQuestionCopy.failure,
            DeleteQuestionCopy.forbiddenTitle,
            DeleteQuestionCopy.forbiddenBody,
            joinQuestionDeleteMessage(why),
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
