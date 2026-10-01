import XCTest

@testable import PDA

final class HomeEditorTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_showsHomeEdit_onlyWithPermission() throws {
        XCTAssertFalse(showsHomeEdit(nil))
        XCTAssertFalse(showsHomeEdit(try user(permissions: [])))
        XCTAssertFalse(showsHomeEdit(try user(permissions: ["edit_faq"])))
        XCTAssertTrue(showsHomeEdit(try user(permissions: ["edit_homepage"])))
        XCTAssertTrue(showsHomeEdit(try user(permissions: [], admin: true)))
    }

    func test_updateHome_patchesContentPm() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        let next = #"{"type":"doc"}"#
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTAssertEqual(routePath(request.url), "/api/community/home/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                let patch = try JSONDecoder().decode(HomePatchBody.self, from: request.httpBody ?? Data())
                XCTAssertEqual(patch.content_pm, next)
                return MockHTTP.json(200, self.homeJSON(pm: next, html: "<p>saved</p>"))
            }
            return MockHTTP.json(200, self.homeJSON(pm: "", html: "<p>old</p>"))
        }
        let model = HomeEditorModel(client: makeClient(tokens), user: try user(permissions: ["edit_homepage"]))
        model.autosaveDelay = .zero
        await model.load()
        model.beginEdit()
        XCTAssertEqual(model.draft, "")
        model.change(next)
        await model.done()
        XCTAssertEqual(model.page?.contentPm, next)
        XCTAssertEqual(model.page?.contentHtml, "<p>saved</p>")
        XCTAssertFalse(model.editing)
        XCTAssertEqual(model.status, .saved)
        XCTAssertEqual(homeAutosaveLabel(model.status), "saved ✓")
    }

    func test_updateHome_403WithoutEditHomepage() async throws {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "update_home"]]])
            }
            return MockHTTP.json(200, self.homeJSON(pm: "old-pm", html: "<p>old</p>"))
        }
        let model = HomeEditorModel(
            client: makeClient(),
            user: try user(permissions: ["edit_homepage"])
        )
        await model.load()
        model.beginEdit()
        model.change("new-pm")
        await model.done()
        XCTAssertEqual(model.page?.contentPm, "old-pm")
        XCTAssertEqual(model.page?.contentHtml, "<p>old</p>")
        XCTAssertEqual(model.status, .error)
        XCTAssertEqual(homeAutosaveLabel(model.status), "couldn't save")
    }

    func test_homeEditor_autosavesDraft() async throws {
        let next = #"{"type":"doc","content":[]}"#
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                let patch = try JSONDecoder().decode(HomePatchBody.self, from: request.httpBody ?? Data())
                XCTAssertEqual(patch.content_pm, next)
                return MockHTTP.json(200, self.homeJSON(pm: next, html: "<p>auto</p>"))
            }
            return MockHTTP.json(200, self.homeJSON(pm: "", html: "<p>old</p>"))
        }
        let model = HomeEditorModel(client: makeClient(), user: try user(permissions: ["edit_homepage"]))
        model.autosaveDelay = .zero
        await model.load()
        model.beginEdit()
        model.change(next)
        let saved = await waitUntil { model.status == .saved }
        XCTAssertTrue(saved)
        XCTAssertEqual(model.page?.contentHtml, "<p>auto</p>")
        XCTAssertTrue(model.editing)
    }

    func test_homeEditor_beginEditRequiresPermission() async throws {
        MockHTTP.handler = { _ in MockHTTP.json(200, self.homeJSON(pm: "pm", html: "<p>hi</p>")) }
        let model = HomeEditorModel(client: makeClient(), user: try user(permissions: ["edit_faq"]))
        await model.load()
        XCTAssertFalse(model.canEdit)
        model.beginEdit()
        XCTAssertFalse(model.editing)
        model.change("nope")
        XCTAssertEqual(model.draft, "")
    }

    func test_homeEditorCopy_isLowercase() {
        let blobs = [
            HomeEditorCopy.edit,
            HomeEditorCopy.done,
            HomeEditorCopy.placeholder,
            HomeEditorCopy.saving,
            HomeEditorCopy.saved,
            HomeEditorCopy.saveError,
        ]
        XCTAssertEqual(HomeEditorCopy.edit, "edit")
        XCTAssertEqual(HomeEditorCopy.done, "done")
        XCTAssertEqual(HomeEditorCopy.placeholder, "home page content")
        XCTAssertEqual(HomeEditorCopy.saving, "saving…")
        XCTAssertEqual(HomeEditorCopy.saved, "saved ✓")
        XCTAssertEqual(HomeEditorCopy.saveError, "couldn't save")
        XCTAssertNil(homeAutosaveLabel(.idle))
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func user(permissions: [String], admin: Bool = false) throws -> SessionUser {
        let roles: [[String: Any]] = admin
            ? [["name": "admin", "is_default": true, "permissions": []]]
            : []
        let payload: [String: Any] = [
            "id": "user-1",
            "is_member": true,
            "permissions": permissions,
            "roles": roles,
        ]
        return try JSONDecoder().decode(SessionUser.self, from: JSONSerialization.data(withJSONObject: payload))
    }

    private func homeJSON(pm: String, html: String) -> [String: String] {
        [
            "content": "hello",
            "content_pm": pm,
            "content_html": html,
            "updated_at": "2024-01-01T00:00:00Z",
        ]
    }

    private func waitUntil(_ ready: @escaping () -> Bool) async -> Bool {
        for _ in 0 ..< 50 {
            if ready() { return true }
            try? await Task.sleep(for: .milliseconds(10))
        }
        return ready()
    }
}

private struct HomePatchBody: Decodable {
    let content_pm: String
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
