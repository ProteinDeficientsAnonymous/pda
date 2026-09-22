import XCTest

@testable import PDA

final class WelcomeTemplateEditorTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_welcomeTemplateURL_keepsTrailingSlash() {
        let url = welcomeTemplateURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/welcome-template/")
        XCTAssertNil(url.query)
    }

    func test_welcomeTemplate_getsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/welcome-template/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "body": "hi ${FIRST_NAME}",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let loaded = try await makeClient(tokens).welcomeTemplate()
        XCTAssertEqual(loaded.body, "hi ${FIRST_NAME}")
        let model = WelcomeTemplateEditorModel(client: makeClient(tokens))
        await model.load()
        XCTAssertEqual(model.body, "hi ${FIRST_NAME}")
        XCTAssertTrue(model.loaded)
    }

    func test_saveWelcomeTemplate_patchesBody() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/welcome-template/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body, ["body": "  hello ${FIRST_NAME}  "])
            return MockHTTP.json(200, [
                "body": "  hello ${FIRST_NAME}  ",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let model = WelcomeTemplateEditorModel(client: makeClient(tokens))
        model.loaded = true
        model.body = "  hello ${FIRST_NAME}  "
        let saved = await model.save()
        XCTAssertTrue(saved)
        XCTAssertEqual(model.toast, "template saved 🌱")
        XCTAssertTrue(model.closed)
        XCTAssertEqual(model.saveLabel, WelcomeTemplateCopy.save)
    }

    func test_saveWelcomeTemplate_emptyBodyDoesNotPatch() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = WelcomeTemplateEditorModel(client: makeClient())
        model.loaded = true
        model.body = "   "
        XCTAssertTrue(model.canSave)
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(called)
        XCTAssertEqual(model.formError, "welcome message body is required")
        XCTAssertNil(model.toast)
        XCTAssertFalse(model.closed)
    }

    func test_saveWelcomeTemplate_overLimitStaysOff() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        XCTAssertEqual(welcomeTemplateMaxLength, 4000)
        XCTAssertFalse(welcomeTemplateOverLimit(String(repeating: "a", count: 4000)))
        XCTAssertTrue(welcomeTemplateOverLimit(String(repeating: "a", count: 4001)))
        XCTAssertEqual(welcomeTemplateCounter(0), "0 / 4000")
        XCTAssertEqual(welcomeTemplateCounter(4001), "4001 / 4000")
        let model = WelcomeTemplateEditorModel(client: makeClient())
        model.loaded = true
        model.body = String(repeating: "a", count: 4001)
        XCTAssertFalse(model.canSave)
        XCTAssertEqual(model.saveLabel, "save")
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(called)
        model.saving = true
        XCTAssertEqual(model.saveLabel, "saving…")
    }

    func test_saveWelcomeTemplate_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = WelcomeTemplateEditorModel(client: makeClient())
        model.loaded = true
        model.body = "hello"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.toast)
        XCTAssertEqual(model.explanationTitle, "edit welcome message")
        XCTAssertEqual(
            model.explanationBody,
            "you need permission to approve join requests to edit the welcome message."
        )
    }

    func test_saveWelcomeTemplate_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = WelcomeTemplateEditorModel(client: makeClient())
        model.loaded = true
        model.body = "hello"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(model.forbidden)
        XCTAssertEqual(model.formError, "couldn't save template — try again")
        XCTAssertNil(model.toast)
    }

    func test_editorCancel_doesNotSave() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "hi", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = WelcomeTemplateEditorModel(client: makeClient())
        model.body = "hello"
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertFalse(called)
        XCTAssertNil(model.toast)
    }

    func test_welcomeTemplateCopy_matchesWeb() {
        XCTAssertEqual(WelcomeTemplateCopy.button, "edit shared welcome template")
        XCTAssertEqual(WelcomeTemplateCopy.title, "edit welcome message")
        XCTAssertEqual(WelcomeTemplateCopy.field, "welcome message body")
        XCTAssertEqual(WelcomeTemplateCopy.helper, "this text is shared with all vetters. changes apply everywhere.")
        XCTAssertEqual(
            WelcomeTemplateCopy.placeholders,
            "available placeholders: ${FIRST_NAME} (recipient's first name), ${SENDER_NAME}, ${MAGIC_LINK}, ${WHATSAPP_LINK}"
        )
        XCTAssertEqual(WelcomeTemplateCopy.saved, "template saved 🌱")
        XCTAssertEqual(WelcomeTemplateCopy.saveError, "couldn't save template — try again")
        let blobs = [
            WelcomeTemplateCopy.button,
            WelcomeTemplateCopy.title,
            WelcomeTemplateCopy.field,
            WelcomeTemplateCopy.helper,
            WelcomeTemplateCopy.saved,
            WelcomeTemplateCopy.cancel,
            WelcomeTemplateCopy.save,
            WelcomeTemplateCopy.saving,
            WelcomeTemplateCopy.required,
            WelcomeTemplateCopy.forbiddenTitle,
            WelcomeTemplateCopy.forbiddenBody,
            WelcomeTemplateCopy.saveError,
        ]
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
