import XCTest

@testable import PDA

final class WhatsAppLinkEditorTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_whatsAppLinkURL_keepsTrailingSlash() {
        let url = whatsAppLinkURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/whatsapp-link/")
        XCTAssertNil(url.query)
    }

    func test_whatsAppLink_getsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/whatsapp-link/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "link": "https://chat.whatsapp.com/abc",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let loaded = try await makeClient(tokens).whatsAppLink()
        XCTAssertEqual(loaded.link, "https://chat.whatsapp.com/abc")
        XCTAssertEqual(loaded.updatedAt, "2026-01-02T03:04:05Z")
        let model = WhatsAppLinkEditorModel(client: makeClient(tokens))
        await model.load()
        XCTAssertEqual(model.link, "https://chat.whatsapp.com/abc")
    }

    func test_saveWhatsAppLink_patchesTrimmedBody() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            XCTAssertEqual(routePath(request.url), "/api/community/whatsapp-link/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body, ["link": "https://chat.whatsapp.com/abc"])
            return MockHTTP.json(200, [
                "link": "https://chat.whatsapp.com/abc",
                "updated_at": "2026-01-02T03:04:05Z",
            ])
        }
        let saved = try await makeClient(tokens).saveWhatsAppLink("  https://chat.whatsapp.com/abc  ")
        XCTAssertEqual(saved.link, "https://chat.whatsapp.com/abc")
        let model = WhatsAppLinkEditorModel(client: makeClient(tokens))
        model.link = "  https://chat.whatsapp.com/abc  "
        let didSave = await model.save()
        XCTAssertTrue(didSave)
        XCTAssertEqual(model.toast, WhatsAppLinkCopy.saved)
        XCTAssertEqual(WhatsAppLinkCopy.saved, "whatsapp link saved")
    }

    func test_saveWhatsAppLink_403ShowsExplanation() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "PATCH")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().saveWhatsAppLink("https://chat.whatsapp.com/abc")
            XCTFail("403 should not save")
        } catch WhatsAppLinkError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
        let model = WhatsAppLinkEditorModel(client: makeClient())
        model.link = "https://chat.whatsapp.com/abc"
        let didSave = await model.save()
        XCTAssertFalse(didSave)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.toast)
        XCTAssertEqual(model.explanationTitle, WhatsAppLinkCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, WhatsAppLinkCopy.forbiddenBody)
        XCTAssertEqual(model.explanationBody, "you need permission to approve join requests to edit this link.")
    }

    func test_whatsAppLinkField_matchesWeb() async {
        XCTAssertEqual(WhatsAppLinkCopy.button, "edit whatsapp link")
        XCTAssertEqual(WhatsAppLinkCopy.title, "edit whatsapp link")
        XCTAssertEqual(WhatsAppLinkCopy.placeholder, "https://chat.whatsapp.com/…")
        XCTAssertEqual(whatsAppLinkMaxLength, 200)
        XCTAssertFalse(whatsAppLinkOverLimit(String(repeating: "a", count: 200)))
        XCTAssertTrue(whatsAppLinkOverLimit(String(repeating: "a", count: 201)))
        XCTAssertNil(whatsAppLinkHostError(""))
        XCTAssertNil(whatsAppLinkHostError("   "))
        XCTAssertNil(whatsAppLinkHostError("https://chat.whatsapp.com/abc"))
        XCTAssertNil(whatsAppLinkHostError("https://wa.me/123"))
        XCTAssertNil(whatsAppLinkHostError("https://whats.app/x"))
        XCTAssertNil(whatsAppLinkHostError("https://www.chat.whatsapp.com/abc"))
        XCTAssertNil(whatsAppLinkHostError("chat.whatsapp.com/abc"))
        XCTAssertEqual(
            whatsAppLinkHostError("https://example.com/x"),
            "whatsapp link must be from chat.whatsapp.com, wa.me, or whats.app"
        )
        XCTAssertEqual(
            whatsAppLinkHostError("https://chat.whatsapp.com"),
            "link must point to a specific page, not just a homepage"
        )
        XCTAssertEqual(
            whatsAppLinkHostError("https://chat.whatsapp.com/"),
            "link must point to a specific page, not just a homepage"
        )

        var patched = false
        MockHTTP.handler = { _ in
            patched = true
            return MockHTTP.json(200, ["link": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let badHost = WhatsAppLinkEditorModel(client: makeClient())
        badHost.link = "https://example.com/group"
        let badHostSaved = await badHost.save()
        XCTAssertFalse(badHostSaved)
        XCTAssertFalse(patched)
        XCTAssertEqual(badHost.formError, WhatsAppLinkCopy.hostError)

        let bare = WhatsAppLinkEditorModel(client: makeClient())
        bare.link = "https://chat.whatsapp.com"
        let bareSaved = await bare.save()
        XCTAssertFalse(bareSaved)
        XCTAssertFalse(patched)

        let tooLong = WhatsAppLinkEditorModel(client: makeClient())
        tooLong.link = String(repeating: "a", count: 201)
        let tooLongSaved = await tooLong.save()
        XCTAssertFalse(tooLongSaved)
        XCTAssertFalse(patched)

        let empty = WhatsAppLinkEditorModel(client: makeClient())
        empty.link = "   "
        let emptySaved = await empty.save()
        XCTAssertTrue(emptySaved)
        XCTAssertTrue(patched)
        XCTAssertEqual(empty.toast, "whatsapp link saved")
    }

    func test_editorCancel_doesNotSave() async {
        var patched = false
        MockHTTP.handler = { _ in
            patched = true
            return MockHTTP.json(200, ["link": "", "updated_at": "2026-01-02T03:04:05Z"])
        }
        let model = WhatsAppLinkEditorModel(client: makeClient())
        model.link = "https://chat.whatsapp.com/abc"
        model.cancel()
        XCTAssertTrue(model.closed)
        XCTAssertFalse(patched)
        XCTAssertNil(model.toast)
    }

    func test_whatsAppLinkCopy_isLowercase() {
        let blobs = [
            WhatsAppLinkCopy.button,
            WhatsAppLinkCopy.title,
            WhatsAppLinkCopy.placeholder,
            WhatsAppLinkCopy.saved,
            WhatsAppLinkCopy.cancel,
            WhatsAppLinkCopy.save,
            WhatsAppLinkCopy.saving,
            WhatsAppLinkCopy.loading,
            WhatsAppLinkCopy.forbiddenTitle,
            WhatsAppLinkCopy.forbiddenBody,
            WhatsAppLinkCopy.hostError,
            WhatsAppLinkCopy.pathError,
            WhatsAppLinkCopy.invalid,
            WhatsAppLinkCopy.loadError,
            WhatsAppLinkCopy.saveError,
        ]
        XCTAssertEqual(WhatsAppLinkCopy.placeholder, "https://chat.whatsapp.com/…")
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
