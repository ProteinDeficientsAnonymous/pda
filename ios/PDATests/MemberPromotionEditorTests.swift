import XCTest

@testable import PDA

final class MemberPromotionEditorTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_memberPromotionURL_keepsTrailingSlash() {
        let url = memberPromotionMessageURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/member-promotion-message/")
        XCTAssertNil(url.query)
    }

    func test_memberPromotion_getsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/member-promotion-message/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "body": "hi ${FIRST_NAME}",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let loaded = try await makeClient(tokens).memberPromotionMessage()
        XCTAssertEqual(loaded.body, "hi ${FIRST_NAME}")
        let model = MemberPromotionEditorModel(client: makeClient(tokens))
        await model.load()
        XCTAssertEqual(model.body, "hi ${FIRST_NAME}")
        XCTAssertTrue(model.loaded)
    }

    func test_saveMemberPromotion_patchesBody() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/member-promotion-message/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body, ["body": "  hello ${FIRST_NAME}  "])
            return MockHTTP.json(200, [
                "body": "  hello ${FIRST_NAME}  ",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let model = MemberPromotionEditorModel(client: makeClient(tokens))
        model.loaded = true
        model.body = "  hello ${FIRST_NAME}  "
        let saved = await model.save()
        XCTAssertTrue(saved)
        XCTAssertEqual(model.toast, "message saved 🌱")
        XCTAssertTrue(model.closed)
        XCTAssertEqual(model.saveLabel, MemberPromotionCopy.save)
    }

    func test_saveMemberPromotion_emptyBodyDoesNotPatch() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = MemberPromotionEditorModel(client: makeClient())
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

    func test_saveMemberPromotion_overLimitStaysOff() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        XCTAssertEqual(memberPromotionMaxLength, 4000)
        XCTAssertFalse(memberPromotionOverLimit(String(repeating: "a", count: 4000)))
        XCTAssertTrue(memberPromotionOverLimit(String(repeating: "a", count: 4001)))
        XCTAssertEqual(memberPromotionCounter(0), "0 / 4000")
        XCTAssertEqual(memberPromotionCounter(4001), "4001 / 4000")
        let model = MemberPromotionEditorModel(client: makeClient())
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

    func test_saveMemberPromotion_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = MemberPromotionEditorModel(client: makeClient())
        model.loaded = true
        model.body = "hello"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.toast)
        XCTAssertEqual(model.explanationTitle, "edit member promotion message")
        XCTAssertEqual(
            model.explanationBody,
            "you need permission to approve join requests to edit the member promotion message."
        )
    }

    func test_saveMemberPromotion_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = MemberPromotionEditorModel(client: makeClient())
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
        let model = MemberPromotionEditorModel(client: makeClient())
        model.body = "hello"
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertFalse(called)
        XCTAssertNil(model.toast)
    }

    func test_memberPromotionCopy_matchesWeb() {
        XCTAssertEqual(MemberPromotionCopy.button, "edit member promotion message")
        XCTAssertEqual(MemberPromotionCopy.title, "edit member promotion message")
        XCTAssertEqual(MemberPromotionCopy.field, "member promotion message body")
        XCTAssertEqual(
            MemberPromotionCopy.helper,
            "sent when a tentatively-approved applicant is manually promoted to full member — this replaces the default message text. they already have a login, so there is no link to share."
        )
        XCTAssertEqual(
            MemberPromotionCopy.placeholders,
            "available placeholders: ${FIRST_NAME} (recipient's first name), ${SENDER_NAME}, ${WHATSAPP_LINK}"
        )
        XCTAssertEqual(MemberPromotionCopy.saved, "message saved 🌱")
        XCTAssertEqual(MemberPromotionCopy.saveError, "couldn't save the message — try again")
        let blobs = [
            MemberPromotionCopy.button,
            MemberPromotionCopy.title,
            MemberPromotionCopy.field,
            MemberPromotionCopy.helper,
            MemberPromotionCopy.saved,
            MemberPromotionCopy.cancel,
            MemberPromotionCopy.save,
            MemberPromotionCopy.saving,
            MemberPromotionCopy.required,
            MemberPromotionCopy.forbiddenTitle,
            MemberPromotionCopy.forbiddenBody,
            MemberPromotionCopy.saveError,
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
