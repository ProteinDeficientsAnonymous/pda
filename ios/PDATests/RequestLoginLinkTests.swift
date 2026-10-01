import XCTest

@testable import PDA

final class RequestLoginLinkTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_requestLoginLink_postsPhoneWithoutBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        let phone = "+12025550101"
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/request-login-link/")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            let body = try JSONDecoder().decode(RequestLoginLinkBody.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.phoneNumber, phone)
            return MockHTTP.json(200, ["detail": "ok", "delivery": "email"])
        }
        XCTAssertEqual(
            requestLoginLinkURL(base: base).absoluteString,
            "https://pda.test/api/community/request-login-link/"
        )
        let model = RequestLoginLinkModel(client: makeClient(tokens), phone: phone)
        await model.submit()
        XCTAssertNil(model.error)
        XCTAssertEqual(model.delivery, "email")
        XCTAssertEqual(model.successMessage, RequestLoginLinkCopy.email)
        XCTAssertTrue(model.successMessage?.contains("🌱") == true)
    }

    func test_requestLoginLink_invalidPhoneDoesNotPost() async {
        var posted = false
        MockHTTP.handler = { _ in
            posted = true
            return MockHTTP.json(200, ["detail": "ok", "delivery": "email"])
        }
        let blank = RequestLoginLinkModel(client: makeClient(), phone: "")
        await blank.submit()
        XCTAssertFalse(posted)
        XCTAssertEqual(blank.error, "enter a valid phone number")
        XCTAssertNil(blank.successMessage)

        let junk = RequestLoginLinkModel(client: makeClient(), phone: "not-a-phone")
        await junk.submit()
        XCTAssertFalse(posted)
        XCTAssertEqual(junk.error, RequestLoginLinkCopy.invalidPhone)
        XCTAssertNil(junk.delivery)
    }

    func test_requestLoginLink_adminDelivery() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, ["detail": "ok", "delivery": "admin"])
        }
        let model = RequestLoginLinkModel(client: makeClient(), phone: "+12025550101")
        await model.submit()
        XCTAssertEqual(model.successMessage, RequestLoginLinkCopy.admin)
        XCTAssertTrue(model.successMessage?.contains("🌱") == true)
        XCTAssertNil(model.cooldownBody)
    }

    func test_requestLoginLink_cooldownDoesNotShowSprout() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, [
                "detail": "ok",
                "delivery": "cooldown",
                "retry_after_seconds": 90,
            ])
        }
        let model = RequestLoginLinkModel(client: makeClient(), phone: "+12025550101")
        await model.submit()
        XCTAssertEqual(model.delivery, "cooldown")
        XCTAssertNil(model.successMessage)
        XCTAssertEqual(model.cooldownBody, RequestLoginLinkCopy.cooldown)
        XCTAssertEqual(requestLoginLinkCountdown(90), "1:30")
        XCTAssertEqual(model.cooldownFollowup, "try again in 1:30")
        XCTAssertFalse(model.cooldownBody?.contains("🌱") == true)
        XCTAssertFalse(model.cooldownFollowup?.contains("🌱") == true)
    }

    func test_requestLoginLink_cooldownReadyWhenRemainingIsZero() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, [
                "detail": "ok",
                "delivery": "cooldown",
                "retry_after_seconds": 0,
            ])
        }
        let model = RequestLoginLinkModel(client: makeClient(), phone: "+12025550101")
        await model.submit()
        XCTAssertEqual(model.cooldownFollowup, RequestLoginLinkCopy.readyNow)
    }

    func test_requestLoginLink_failureUsesFallback() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, [:])
        }
        let model = RequestLoginLinkModel(client: makeClient(), phone: "+12025550101")
        await model.submit()
        XCTAssertEqual(model.error, "couldn't send the request — try again")
        XCTAssertNil(model.delivery)
        XCTAssertNil(model.successMessage)
    }

    func test_requestLoginLink_stringDetailIsTheError() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(429, ["detail": "slow down"])
        }
        let model = RequestLoginLinkModel(client: makeClient(), phone: "+12025550101")
        await model.submit()
        XCTAssertEqual(model.error, "slow down")
        XCTAssertNil(model.delivery)
    }

    func test_requestLoginLink_copyAndNoSuccessBeforeSubmit() {
        let model = RequestLoginLinkModel(client: makeClient(), phone: "+12025550101")
        XCTAssertNil(model.successMessage)
        XCTAssertNil(model.delivery)
        XCTAssertEqual(RequestLoginLinkCopy.button, "request a login link")
        XCTAssertEqual(RequestLoginLinkCopy.title, "request a login link")
        XCTAssertEqual(
            RequestLoginLinkCopy.hint,
            "enter your phone number and we'll send a one-tap login link to the email on file"
        )
        XCTAssertEqual(RequestLoginLinkCopy.phone, "phone number")
        XCTAssertEqual(RequestLoginLinkCopy.cancel, "cancel")
        XCTAssertEqual(RequestLoginLinkCopy.submit, "request link")
        XCTAssertEqual(RequestLoginLinkCopy.submitting, "requesting…")
        XCTAssertEqual(RequestLoginLinkCopy.done, "done")
        XCTAssertEqual(
            RequestLoginLinkCopy.email,
            "if there's an account for that number, we sent a login link to the email on file — check your inbox, including spam 🌱"
        )
        XCTAssertEqual(
            RequestLoginLinkCopy.admin,
            "if there's an account for that number, an admin will follow up with your login link — sit tight 🌱"
        )
        XCTAssertEqual(
            RequestLoginLinkCopy.cooldown,
            "we didn't send a new link — you requested one just a moment ago, and it's still valid. check your inbox, including spam."
        )
        let lines = [
            RequestLoginLinkCopy.button,
            RequestLoginLinkCopy.title,
            RequestLoginLinkCopy.hint,
            RequestLoginLinkCopy.phone,
            RequestLoginLinkCopy.cancel,
            RequestLoginLinkCopy.submit,
            RequestLoginLinkCopy.submitting,
            RequestLoginLinkCopy.done,
            RequestLoginLinkCopy.invalidPhone,
            RequestLoginLinkCopy.email,
            RequestLoginLinkCopy.admin,
            RequestLoginLinkCopy.cooldown,
            RequestLoginLinkCopy.readyNow,
            RequestLoginLinkCopy.failure,
        ]
        for line in lines {
            XCTAssertEqual(line, line.lowercased())
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore = MemoryTokenStore()) -> SessionClient {
        SessionClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private struct RequestLoginLinkBody: Decodable {
    let phoneNumber: String

    enum CodingKeys: String, CodingKey {
        case phoneNumber = "phone_number"
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
