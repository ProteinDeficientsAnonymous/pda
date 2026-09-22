import XCTest

@testable import PDA

final class TentativeApprovalEditorTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_tentativeApprovalURL_keepsTrailingSlash() {
        let url = tentativeApprovalMessageURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/tentative-approval-message/")
        XCTAssertNil(url.query)
    }

    func test_tentativeApproval_getsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/tentative-approval-message/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "body": "hi ${FIRST_NAME}",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let loaded = try await makeClient(tokens).tentativeApprovalMessage()
        XCTAssertEqual(loaded.body, "hi ${FIRST_NAME}")
        let model = TentativeApprovalEditorModel(client: makeClient(tokens))
        await model.load()
        XCTAssertEqual(model.body, "hi ${FIRST_NAME}")
        XCTAssertTrue(model.loaded)
    }

    func test_saveTentativeApproval_patchesBody() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/tentative-approval-message/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body, ["body": "  hello ${FIRST_NAME}  "])
            return MockHTTP.json(200, [
                "body": "  hello ${FIRST_NAME}  ",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let model = TentativeApprovalEditorModel(client: makeClient(tokens))
        model.loaded = true
        model.body = "  hello ${FIRST_NAME}  "
        let saved = await model.save()
        XCTAssertTrue(saved)
        XCTAssertEqual(model.toast, "message saved 🌱")
        XCTAssertTrue(model.closed)
        XCTAssertEqual(model.saveLabel, TentativeApprovalCopy.save)
    }

    func test_saveTentativeApproval_emptyBodyDoesNotPatch() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = TentativeApprovalEditorModel(client: makeClient())
        model.loaded = true
        model.body = "   "
        XCTAssertTrue(model.canSave)
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(called)
        XCTAssertEqual(model.formError, "message body is required")
        XCTAssertNil(model.toast)
        XCTAssertFalse(model.closed)
    }

    func test_saveTentativeApproval_overLimitStaysOff() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        XCTAssertEqual(tentativeApprovalMaxLength, 4000)
        XCTAssertFalse(tentativeApprovalOverLimit(String(repeating: "a", count: 4000)))
        XCTAssertTrue(tentativeApprovalOverLimit(String(repeating: "a", count: 4001)))
        XCTAssertEqual(tentativeApprovalCounter(0), "0 / 4000")
        XCTAssertEqual(tentativeApprovalCounter(4001), "4001 / 4000")
        let model = TentativeApprovalEditorModel(client: makeClient())
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

    func test_saveTentativeApproval_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = TentativeApprovalEditorModel(client: makeClient())
        model.loaded = true
        model.body = "hello"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.toast)
        XCTAssertEqual(model.explanationTitle, "edit tentative approval message")
        XCTAssertEqual(
            model.explanationBody,
            "you need permission to approve join requests to edit the tentative approval message."
        )
    }

    func test_saveTentativeApproval_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = TentativeApprovalEditorModel(client: makeClient())
        model.loaded = true
        model.body = "hello"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(model.forbidden)
        XCTAssertEqual(model.formError, "couldn't save the message — try again")
        XCTAssertNil(model.toast)
    }

    func test_editorCancel_doesNotSave() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "hi", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = TentativeApprovalEditorModel(client: makeClient())
        model.body = "hello"
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertFalse(called)
        XCTAssertNil(model.toast)
    }

    func test_tentativeApprovalCopy_matchesWeb() {
        XCTAssertEqual(TentativeApprovalCopy.button, "edit tentative approval message")
        XCTAssertEqual(TentativeApprovalCopy.title, "edit tentative approval message")
        XCTAssertEqual(TentativeApprovalCopy.field, "tentative approval message body")
        XCTAssertEqual(
            TentativeApprovalCopy.helper,
            "sent when someone is tentatively approved — this replaces the default message text."
        )
        XCTAssertEqual(
            TentativeApprovalCopy.placeholders,
            "available placeholders: ${FIRST_NAME} (recipient's first name), ${SENDER_NAME}, ${MAGIC_LINK} (their one-time sign in link), ${WHATSAPP_LINK}"
        )
        XCTAssertEqual(TentativeApprovalCopy.saved, "message saved 🌱")
        XCTAssertEqual(TentativeApprovalCopy.saveError, "couldn't save the message — try again")
        let blobs = [
            TentativeApprovalCopy.button,
            TentativeApprovalCopy.title,
            TentativeApprovalCopy.field,
            TentativeApprovalCopy.helper,
            TentativeApprovalCopy.saved,
            TentativeApprovalCopy.cancel,
            TentativeApprovalCopy.save,
            TentativeApprovalCopy.saving,
            TentativeApprovalCopy.required,
            TentativeApprovalCopy.forbiddenTitle,
            TentativeApprovalCopy.forbiddenBody,
            TentativeApprovalCopy.saveError,
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
