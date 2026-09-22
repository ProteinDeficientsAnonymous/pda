import XCTest

@testable import PDA

final class MemberPromotionEmailEditorTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_memberPromotionEmailURL_keepsTrailingSlash() {
        let url = memberPromotionEmailURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/member-promotion-email/")
        XCTAssertNil(url.query)
    }

    func test_memberPromotionEmail_getsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/member-promotion-email/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "body": "hi ${FIRST_NAME}",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let loaded = try await makeClient(tokens).memberPromotionEmail()
        XCTAssertEqual(loaded.body, "hi ${FIRST_NAME}")
        let model = MemberPromotionEmailEditorModel(client: makeClient(tokens))
        await model.load()
        XCTAssertEqual(model.body, "hi ${FIRST_NAME}")
        XCTAssertTrue(model.loaded)
    }

    func test_saveMemberPromotionEmail_patchesBody() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/member-promotion-email/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body, ["body": "  hello ${FIRST_NAME}  "])
            return MockHTTP.json(200, [
                "body": "  hello ${FIRST_NAME}  ",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let model = MemberPromotionEmailEditorModel(client: makeClient(tokens))
        model.loaded = true
        model.body = "  hello ${FIRST_NAME}  "
        let saved = await model.save()
        XCTAssertTrue(saved)
        XCTAssertEqual(model.toast, "email saved 🌱")
        XCTAssertTrue(model.closed)
        XCTAssertEqual(model.saveLabel, MemberPromotionEmailCopy.save)
    }

    func test_saveMemberPromotionEmail_emptyBodyDoesNotPatch() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = MemberPromotionEmailEditorModel(client: makeClient())
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

    func test_saveMemberPromotionEmail_overLimitStaysOff() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        XCTAssertEqual(memberPromotionEmailMaxLength, 4000)
        XCTAssertFalse(memberPromotionEmailOverLimit(String(repeating: "a", count: 4000)))
        XCTAssertTrue(memberPromotionEmailOverLimit(String(repeating: "a", count: 4001)))
        XCTAssertEqual(memberPromotionEmailCounter(0), "0 / 4000")
        XCTAssertEqual(memberPromotionEmailCounter(4001), "4001 / 4000")
        let model = MemberPromotionEmailEditorModel(client: makeClient())
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

    func test_saveMemberPromotionEmail_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = MemberPromotionEmailEditorModel(client: makeClient())
        model.loaded = true
        model.body = "hello"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.toast)
        XCTAssertEqual(model.explanationTitle, "edit member promotion email")
        XCTAssertEqual(
            model.explanationBody,
            "you need permission to approve join requests to edit the member promotion email."
        )
    }

    func test_saveMemberPromotionEmail_failureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = MemberPromotionEmailEditorModel(client: makeClient())
        model.loaded = true
        model.body = "hello"
        let saved = await model.save()
        XCTAssertFalse(saved)
        XCTAssertFalse(model.forbidden)
        XCTAssertEqual(model.formError, "couldn't save the email — try again")
        XCTAssertNil(model.toast)
    }

    func test_editorCancel_doesNotSave() async {
        var called = false
        MockHTTP.handler = { _ in
            called = true
            return MockHTTP.json(200, ["body": "hi", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = MemberPromotionEmailEditorModel(client: makeClient())
        model.body = "hello"
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertFalse(called)
        XCTAssertNil(model.toast)
    }

    func test_memberPromotionEmailCopy_matchesWeb() {
        XCTAssertEqual(MemberPromotionEmailCopy.button, "edit member promotion email")
        XCTAssertEqual(MemberPromotionEmailCopy.title, "edit member promotion email")
        XCTAssertEqual(MemberPromotionEmailCopy.field, "member promotion email body")
        XCTAssertEqual(
            MemberPromotionEmailCopy.helper,
            "sent automatically when a tentatively-approved applicant becomes a full member — on event check-in or manual promotion. links in the body are turned into clickable links."
        )
        XCTAssertEqual(
            MemberPromotionEmailCopy.placeholders,
            "available placeholders: ${FIRST_NAME} (recipient's first name), ${WHATSAPP_LINK}"
        )
        XCTAssertEqual(MemberPromotionEmailCopy.saved, "email saved 🌱")
        XCTAssertEqual(MemberPromotionEmailCopy.saveError, "couldn't save the email — try again")
        let blobs = [
            MemberPromotionEmailCopy.button,
            MemberPromotionEmailCopy.title,
            MemberPromotionEmailCopy.field,
            MemberPromotionEmailCopy.helper,
            MemberPromotionEmailCopy.saved,
            MemberPromotionEmailCopy.cancel,
            MemberPromotionEmailCopy.save,
            MemberPromotionEmailCopy.saving,
            MemberPromotionEmailCopy.required,
            MemberPromotionEmailCopy.forbiddenTitle,
            MemberPromotionEmailCopy.forbiddenBody,
            MemberPromotionEmailCopy.saveError,
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
