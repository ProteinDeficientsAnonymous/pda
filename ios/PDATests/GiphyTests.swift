import XCTest

@testable import PDA

final class GiphyTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_giphy_searchesWithBearerAndMapsResults() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/giphy/search/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let items = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems ?? []
            XCTAssertEqual(items.first { $0.name == "q" }?.value, "sprout")
            XCTAssertEqual(items.first { $0.name == "limit" }?.value, "24")
            return MockHTTP.json(200, [
                "results": [
                    [
                        "id": "g1",
                        "title": "Sprout",
                        "preview_url": "https://img.test/g1.gif",
                        "original_url": "https://img.test/g1-full.gif",
                        "source": "gif",
                    ],
                    [
                        "id": "p1",
                        "title": "Park",
                        "preview_url": "https://img.test/p1.jpg",
                        "original_url": "https://img.test/p1-full.jpg",
                        "source": "photo",
                    ],
                ],
            ])
        }
        let model = ImageSearchModel(client: makeClient(tokens))
        await model.search("  sprout ")
        XCTAssertNil(model.error)
        XCTAssertEqual(model.results.map(\.id), ["g1", "p1"])
        XCTAssertEqual(model.results[0].previewURL, "https://img.test/g1.gif")
        XCTAssertEqual(model.results[0].originalURL, "https://img.test/g1-full.gif")
        XCTAssertEqual(model.results[0].source, "gif")
        XCTAssertTrue(model.showsGiphyMark)
        XCTAssertEqual(model.empty, nil)
    }

    func test_giphy_blankQueryOmitsQAndHidesMarkForPhotos() async {
        MockHTTP.handler = { request in
            let items = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems ?? []
            XCTAssertNil(items.first { $0.name == "q" })
            XCTAssertEqual(items.first { $0.name == "limit" }?.value, "24")
            return MockHTTP.json(200, [
                "results": [[
                    "id": "p1",
                    "title": "Still",
                    "preview_url": "https://img.test/p.jpg",
                    "original_url": "https://img.test/p-full.jpg",
                    "source": "photo",
                ]],
            ])
        }
        let model = ImageSearchModel(client: makeClient())
        await model.search("   ")
        XCTAssertFalse(model.showsGiphyMark)
        XCTAssertNil(model.empty)
    }

    func test_giphy_403IsThePermissionGate() async {
        var saw = false
        MockHTTP.handler = { _ in
            saw = true
            return MockHTTP.json(403, ["detail": [["code": "auth.guidelines_consent_required"]]])
        }
        let model = ImageSearchModel(client: makeClient())
        await model.search("party")
        XCTAssertTrue(saw)
        XCTAssertTrue(model.results.isEmpty)
        XCTAssertEqual(model.error, "couldn't search images — try again")
    }

    func test_giphy_emptySearchAndUploadRules() async {
        MockHTTP.handler = { _ in MockHTTP.json(200, ["results": []]) }
        let model = ImageSearchModel(client: makeClient())
        await model.search("nope")
        XCTAssertEqual(model.empty, "nothing found — try another search")
        XCTAssertEqual(photoUploadError(mime: "image/tiff", bytes: 10), "pick a jpeg, png, webp, gif, or heic image")
        XCTAssertEqual(photoUploadError(mime: "image/jpeg", bytes: 10 * 1024 * 1024 + 1), "photo must be under 10 mb")
        XCTAssertNil(photoUploadError(mime: "image/gif", bytes: 100))
        XCTAssertEqual(ImageSearchCopy.title, "choose an image")
        XCTAssertEqual(ImageSearchCopy.library, "library")
        XCTAssertEqual(ImageSearchCopy.upload, "upload your own")
        XCTAssertEqual(ImageSearchCopy.placeholder, "search gifs and photos")
        XCTAssertEqual(ImageSearchCopy.searching, "searching…")
        XCTAssertEqual(ImageSearchCopy.drop, "tap or drop a photo")
        XCTAssertEqual(ImageSearchCopy.cancel, "cancel")
        XCTAssertEqual(ImageSearchCopy.loadError, "couldn't load that image — try another")
        XCTAssertEqual(ImageSearchCopy.attribution, "powered by giphy")
        for line in [
            ImageSearchCopy.title,
            ImageSearchCopy.library,
            ImageSearchCopy.upload,
            ImageSearchCopy.placeholder,
            model.empty ?? "",
        ] {
            XCTAssertEqual(line, line.lowercased())
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore = MemoryTokenStore()) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
