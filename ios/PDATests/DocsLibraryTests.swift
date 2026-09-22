import XCTest

@testable import PDA

final class DocsLibraryTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_docsLibraryURL_keepsTrailingSlash() {
        let url = docsLibraryURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/docs/folders/")
        XCTAssertNil(url.query)
    }

    func test_docsLibrary_getsFoldersWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/docs/folders/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                [
                    "id": "f1",
                    "name": "Guides",
                    "documents": [["id": "d1", "title": "Welcome"]],
                    "children": [
                        [
                            "id": "f2",
                            "name": "Drafts",
                            "documents": [["id": "d2", "title": "Notes"]],
                            "children": [],
                        ],
                    ],
                ],
            ])
        }
        let folders = try await makeClient(tokens).docsLibrary()
        XCTAssertEqual(docsLibraryLines(folders), ["guides", "welcome", "drafts", "notes"])
    }

    func test_docsLibrary_403WithoutManageDocuments() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().docsLibrary()
            XCTFail("403 should not return the library")
        } catch DocsLibraryError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_docsLibraryModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = DocsLibraryModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.folders.isEmpty)
        XCTAssertEqual(model.explanationTitle, DocsLibraryCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, DocsLibraryCopy.forbiddenBody)
    }

    func test_docsTile_opensListOnly() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "manage_documents",
            "edit_join_questions",
        ]))
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .docs }.map(\.id), ["docs"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == nil }.map(\.id), ["join-form"])
    }

    func test_docsLibraryCopy_isLowercase() {
        let blobs = [
            DocsLibraryCopy.title,
            DocsLibraryCopy.loading,
            DocsLibraryCopy.error,
            DocsLibraryCopy.empty,
            DocsLibraryCopy.forbiddenTitle,
            DocsLibraryCopy.forbiddenBody,
        ]
        XCTAssertEqual(DocsLibraryCopy.title, "docs")
        XCTAssertEqual(DocsLibraryCopy.error, "couldn't load the docs — try refreshing")
        XCTAssertEqual(DocsLibraryCopy.empty, "nothing here yet 🌿")
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

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
