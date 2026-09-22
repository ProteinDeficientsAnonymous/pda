import XCTest

@testable import PDA

final class GeocodeTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_geocode_getsQueryWithBearerAndParsesPhoton() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/geocode/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let items = URLComponents(url: request.url!, resolvingAgainstBaseURL: false)?.queryItems ?? []
            XCTAssertEqual(items.first { $0.name == "q" }?.value, "central park")
            XCTAssertEqual(items.first { $0.name == "limit" }?.value, "5")
            return MockHTTP.json(200, [
                "features": [
                    [
                        "geometry": ["coordinates": [-73.9654, 40.7829]],
                        "properties": [
                            "name": "Central Park",
                            "housenumber": "1",
                            "street": "5th Ave",
                            "city": "New York",
                        ],
                    ],
                ],
            ])
        }
        let model = LocationSearchModel(client: makeClient(tokens))
        await model.search("  central park  ")
        XCTAssertEqual(model.results.count, 1)
        XCTAssertEqual(model.results[0].name, "Central Park")
        XCTAssertEqual(model.results[0].subtitle, "1 5th Ave")
        XCTAssertEqual(model.results[0].fullAddress, "central park, 1 5th ave, ny")
        XCTAssertEqual(model.results[0].latitude, 40.7829)
        XCTAssertEqual(model.results[0].longitude, -73.9654)
        model.choose(model.results[0])
        XCTAssertEqual(model.location, "central park, 1 5th ave, ny")
        XCTAssertEqual(model.latitude, 40.7829)
        XCTAssertEqual(model.longitude, -73.9654)
    }

    func test_geocode_shortQueryDoesNotRequestAndClearsPin() async {
        var saw = false
        MockHTTP.handler = { _ in
            saw = true
            return MockHTTP.json(200, ["features": []])
        }
        let model = LocationSearchModel(client: makeClient())
        model.latitude = 1
        model.longitude = 2
        await model.search("ny")
        XCTAssertFalse(saw)
        XCTAssertTrue(model.results.isEmpty)
        XCTAssertNil(model.latitude)
        XCTAssertNil(model.longitude)
        XCTAssertEqual(model.location, "ny")
    }

    func test_geocode_403IsThePermissionGate() async {
        var saw = false
        MockHTTP.handler = { request in
            saw = true
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(403, ["detail": [["code": "auth.account_paused"]]])
        }
        let tokens = MemoryTokenStore()
        try? tokens.save("access-jwt")
        let model = LocationSearchModel(client: makeClient(tokens))
        await model.search("prospect park")
        XCTAssertTrue(saw)
        XCTAssertTrue(model.results.isEmpty)
        XCTAssertNil(model.latitude)
    }

    func test_geocode_dropsNamelessFeatures() {
        let parsed = geocodeResults(from: [
            "features": [
                ["geometry": ["coordinates": [1.0, 2.0]], "properties": ["city": "Queens"]],
                ["geometry": ["coordinates": [-74.0, 40.7]], "properties": ["street": "Broadway", "city": "Brooklyn"]],
            ],
        ])
        XCTAssertEqual(parsed.map(\.fullAddress), ["broadway, brooklyn"])
        XCTAssertEqual(GeocodeCopy.label, "location")
        XCTAssertEqual(GeocodeCopy.placeholder, "search an address or place")
        XCTAssertEqual(GeocodeCopy.label, GeocodeCopy.label.lowercased())
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
