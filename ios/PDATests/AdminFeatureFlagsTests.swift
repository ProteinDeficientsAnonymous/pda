import XCTest

@testable import PDA

final class AdminFeatureFlagsTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_featureFlagURLs_keepTrailingSlash() {
        XCTAssertEqual(
            featureFlagsURL(base: base).absoluteString,
            "https://pda.test/api/community/feature-flags/"
        )
        XCTAssertEqual(
            featureFlagURL(base: base, key: "host_attendance_report").absoluteString,
            "https://pda.test/api/community/feature-flags/host_attendance_report/"
        )
        XCTAssertEqual(versionURL(base: base).absoluteString, "https://pda.test/api/community/version/")
        XCTAssertNil(featureFlagsURL(base: base).query)
    }

    func test_featureFlagChoices_matchWeb() {
        XCTAssertEqual(featureFlagChoices.map(\.key), [
            "host_attendance_report",
            "admin_attendance_analytics",
            "event_payment_confirmation",
        ])
        XCTAssertEqual(featureFlagChoices.map(\.label), [
            "host attendance report",
            "admin attendance analytics",
            "event payment confirmation",
        ])
    }

    func test_featureFlags_getsFlagsAndVersion() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            switch routePath(request.url) {
            case "/api/community/feature-flags/":
                XCTAssertEqual(request.httpMethod, "GET")
                return MockHTTP.json(200, ["flags": ["host_attendance_report": true]])
            case "/api/community/version/":
                XCTAssertEqual(request.httpMethod, "GET")
                return MockHTTP.json(200, [
                    "commit_sha": "abc",
                    "commit_sha_short": "abc",
                    "environment": "Staging",
                ])
            default:
                XCTFail("unexpected \(request.url?.path ?? "")")
                return MockHTTP.json(500, [:])
            }
        }
        let model = AdminFeatureFlagsModel(client: makeClient(tokens))
        await model.load()
        XCTAssertEqual(model.flags["host_attendance_report"], true)
        XCTAssertEqual(featureFlagEnabled(model.flags, "admin_attendance_analytics"), false)
        XCTAssertEqual(model.environmentLine, "environment: staging")
        XCTAssertNil(model.error)
    }

    func test_featureFlags_versionStillLoading() async {
        MockHTTP.handler = { request in
            if routePath(request.url) == "/api/community/version/" {
                return MockHTTP.json(500, [:])
            }
            return MockHTTP.json(200, ["flags": [:]])
        }
        let model = AdminFeatureFlagsModel(client: makeClient())
        await model.load()
        XCTAssertEqual(model.environmentLine, "loading environment…")
        XCTAssertNil(model.error)
    }

    func test_featureFlags_loadFailure() async {
        MockHTTP.handler = { _ in MockHTTP.json(500, ["detail": "nope"]) }
        let model = AdminFeatureFlagsModel(client: makeClient())
        await model.load()
        XCTAssertEqual(model.error, "couldn't load feature flags — try refreshing")
        XCTAssertFalse(model.forbidden)
    }

    func test_setFeatureFlag_patchesEnabled() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                XCTAssertEqual(routePath(request.url), "/api/community/feature-flags/host_attendance_report/")
                XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
                let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: Any]
                XCTAssertEqual(body?["enabled"] as? Bool, true)
                return MockHTTP.json(200, [
                    "flags": [
                        "host_attendance_report": true,
                        "admin_attendance_analytics": false,
                        "event_payment_confirmation": false,
                    ],
                ])
            }
            return MockHTTP.json(200, ["flags": ["host_attendance_report": false]])
        }
        let model = AdminFeatureFlagsModel(client: makeClient(tokens))
        await model.load()
        await model.set("host_attendance_report", enabled: true)
        XCTAssertEqual(model.flags["host_attendance_report"], true)
        XCTAssertFalse(model.forbidden)
        XCTAssertFalse(model.saving)
    }

    func test_setFeatureFlag_403WithoutManageFeatureFlags() async {
        MockHTTP.handler = { request in
            if request.httpMethod == "PATCH" {
                return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
            }
            return MockHTTP.json(200, ["flags": ["host_attendance_report": false]])
        }
        let model = AdminFeatureFlagsModel(client: makeClient())
        await model.load()
        await model.set("host_attendance_report", enabled: true)
        XCTAssertTrue(model.forbidden)
        XCTAssertEqual(model.flags["host_attendance_report"], false)
        XCTAssertEqual(model.explanationTitle, "feature flags")
        XCTAssertEqual(
            model.explanationBody,
            "you need permission to manage feature flags to change a flag."
        )
    }

    func test_featureFlagsTile_hiddenWithoutPermission() throws {
        XCTAssertFalse(
            adminHubTiles(for: try user(permissions: ["manage_events"])).map(\.label).contains("feature flags")
        )
        let tiles = adminHubTiles(for: try user(permissions: ["manage_feature_flags"]))
        XCTAssertEqual(tiles.map(\.label), ["feature flags"])
        XCTAssertEqual(tiles.map(\.detail), ["toggle dark-launched features"])
        XCTAssertEqual(tiles.map { adminHubDestination(for: $0) }, [.featureFlags])
    }

    func test_featureFlagsCopy_isLowercase() {
        let blobs = [
            AdminFeatureFlagsCopy.title,
            AdminFeatureFlagsCopy.loading,
            AdminFeatureFlagsCopy.error,
            AdminFeatureFlagsCopy.forbiddenTitle,
            AdminFeatureFlagsCopy.forbiddenBody,
            "loading environment…",
        ] + featureFlagChoices.map(\.label)
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
