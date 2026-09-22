import XCTest

@testable import PDA

final class DocDetailTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_docDetailURL_keepsTrailingSlash() {
        let url = docDetailURL(base: base, id: "d1")
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/docs/d1/")
        XCTAssertNil(url.query)
    }

    func test_document_getsTitleAndHtmlWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/docs/d1/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "id": "d1",
                "title": "Welcome",
                "content_html": "<p>Hello</p>",
            ])
        }
        let doc = try await makeClient(tokens).document(id: "d1")
        XCTAssertEqual(doc.id, "d1")
        XCTAssertEqual(doc.title, "Welcome")
        XCTAssertEqual(doc.contentHtml, "<p>Hello</p>")
        XCTAssertEqual(docDetailTitle(doc), "welcome")
    }

    func test_document_403WithoutManageDocuments() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().document(id: "d1")
            XCTFail("403 should not return the document")
        } catch DocDetailError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_docDetailModel_forbiddenShowsExplanationNotBody() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = DocDetailModel(client: makeClient(), docId: "d1")
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.document)
        XCTAssertEqual(model.explanationTitle, DocDetailCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, DocDetailCopy.forbiddenBody)
    }

    func test_docDetailCopy_isLowercase() {
        let blobs = [
            DocDetailCopy.loading,
            DocDetailCopy.error,
            DocDetailCopy.forbiddenTitle,
            DocDetailCopy.forbiddenBody,
        ]
        XCTAssertEqual(DocDetailCopy.error, "couldn't load this doc — try refreshing")
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
