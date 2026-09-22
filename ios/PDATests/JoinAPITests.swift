import Foundation
import XCTest

@testable import PDA

final class JoinAPITests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func setUp() {
        super.setUp()
        MockHTTP.handler = nil
    }

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_joinFormURL_keepsTrailingSlash() {
        XCTAssertEqual(
            joinFormURL(base: base).absoluteString,
            "https://pda.test/api/community/join-form/"
        )
        XCTAssertEqual(
            joinRequestURL(base: base).absoluteString,
            "https://pda.test/api/community/join-request/"
        )
    }

    func test_joinForm_getsQuestionsWithoutAuthAndSortsByDisplayOrder() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/join-form/")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            return MockHTTP.json(200, [
                [
                    "id": "q-2",
                    "label": "how did you hear about us?",
                    "field_type": "textarea",
                    "options": [] as [String],
                    "required": false,
                    "display_order": 1,
                ],
                [
                    "id": "q-1",
                    "label": "why pda?",
                    "field_type": "text",
                    "options": [] as [String],
                    "required": true,
                    "display_order": 0,
                ],
                [
                    "id": "q-3",
                    "label": "diet",
                    "field_type": "select",
                    "options": ["vegan", "mostly vegan"],
                    "required": true,
                    "display_order": 2,
                ],
            ])
        }
        let questions = try await makeClient().joinForm()
        XCTAssertEqual(questions.map(\.id), ["q-1", "q-2", "q-3"])
        XCTAssertEqual(questions[0].label, "why pda?")
        XCTAssertEqual(questions[0].fieldType, "text")
        XCTAssertTrue(questions[0].required)
        XCTAssertEqual(questions[1].fieldType, "textarea")
        XCTAssertEqual(questions[2].options, ["vegan", "mostly vegan"])
    }

    func test_submitJoinRequest_postsFieldsWithoutAuthOrSignup() async throws {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/join-request/")
            XCTAssertNil(request.value(forHTTPHeaderField: "Authorization"))
            let body = try XCTUnwrap(request.json)
            XCTAssertEqual(body["first_name"] as? String, "ada")
            XCTAssertEqual(body["last_name"] as? String, "lovelace")
            XCTAssertEqual(body["phone_number"] as? String, "+15555550999")
            XCTAssertEqual(body["email"] as? String, "ada@pda.test")
            XCTAssertEqual(body["sms_consent"] as? Bool, true)
            XCTAssertEqual(body["guidelines_consent"] as? Bool, true)
            XCTAssertEqual(body["website"] as? String, "")
            XCTAssertNil(body["password"])
            let answers = try XCTUnwrap(body["answers"] as? [String: Any])
            XCTAssertEqual(answers["q-1"] as? String, "community")
            return MockHTTP.json(201, ["id": "jr-1", "status": "pending"])
        }
        try await makeClient().submitJoinRequest(
            firstName: "ada",
            lastName: "lovelace",
            phone: "+15555550999",
            email: "ada@pda.test",
            answers: ["q-1": "community"],
            smsConsent: true,
            guidelinesConsent: true
        )
    }

    func test_submitJoinRequest_mapsPhoneAlreadyInvited() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(409, ["detail": [["code": "join_request.phone_already_invited", "field": NSNull()]]])
        }
        do {
            try await makeClient().submitJoinRequest(
                firstName: "ada",
                lastName: "lovelace",
                phone: "+15555550100",
                email: "ada@pda.test",
                answers: [:],
                smsConsent: true,
                guidelinesConsent: true
            )
            XCTFail("already invited should throw")
        } catch JoinError.alreadyInvited {
            // expected
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_joinCopy_isLowercase() {
        let blobs = [
            JoinCopy.title,
            JoinCopy.requestToJoin,
            JoinCopy.subtitle,
            JoinCopy.firstName,
            JoinCopy.lastName,
            JoinCopy.phone,
            JoinCopy.phoneHint,
            JoinCopy.email,
            JoinCopy.smsConsent,
            JoinCopy.guidelinesConsent,
            JoinCopy.submit,
            JoinCopy.submitting,
            JoinCopy.loading,
            JoinCopy.error,
            JoinCopy.successTitle,
            JoinCopy.successBody,
            JoinCopy.backHome,
            JoinCopy.firstNameRequired,
            JoinCopy.lastNameRequired,
            JoinCopy.phoneRequired,
            JoinCopy.emailRequired,
            JoinCopy.emailInvalid,
            JoinCopy.smsRequired,
            JoinCopy.guidelinesRequired,
            JoinCopy.alreadyInvited,
            JoinCopy.signIn,
        ]
        XCTAssertEqual(JoinCopy.title, "request to join pda")
        XCTAssertEqual(JoinCopy.submit, "submit request")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    func test_joinSuccessCopy_matchesWeb() {
        XCTAssertEqual(JoinCopy.successTitle, "request received!")
        XCTAssertEqual(
            JoinCopy.successBody,
            "a vetting member will review your request and reach out soon"
        )
        XCTAssertEqual(JoinCopy.backHome, "back to home")
    }

    func test_joinModel_blocksSubmitWhenRequiredMissing() async {
        let model = JoinModel(client: makeClient())
        model.questions = [
            JoinQuestion(id: "q-1", label: "why pda?", fieldType: "text", required: true, options: [], displayOrder: 0),
        ]
        MockHTTP.handler = { _ in
            XCTFail("should not post until valid")
            return MockHTTP.json(201, ["id": "jr-1"])
        }
        await model.submit()
        XCTAssertEqual(model.errors["firstName"], JoinCopy.firstNameRequired)
        XCTAssertEqual(model.errors["lastName"], JoinCopy.lastNameRequired)
        XCTAssertEqual(model.errors["phone"], JoinCopy.phoneRequired)
        XCTAssertEqual(model.errors["email"], JoinCopy.emailRequired)
        XCTAssertEqual(model.errors["smsConsent"], JoinCopy.smsRequired)
        XCTAssertEqual(model.errors["guidelinesConsent"], JoinCopy.guidelinesRequired)
        XCTAssertEqual(model.errors["q-1"], "required")
        XCTAssertEqual(model.destination, .form)
    }

    func test_joinModel_submitsThenShowsSuccess() async {
        MockHTTP.handler = { request in
            if routePath(request.url) == "/api/community/join-form/" {
                return MockHTTP.json(200, [] as [Any])
            }
            XCTAssertEqual(routePath(request.url), "/api/community/join-request/")
            return MockHTTP.json(201, ["id": "jr-1", "status": "pending"])
        }
        let model = JoinModel(client: makeClient())
        model.firstName = " ada "
        model.lastName = " lovelace "
        model.phone = " +15555550999 "
        model.email = " ada@pda.test "
        model.smsConsent = true
        model.guidelinesConsent = true
        await model.submit()
        XCTAssertEqual(model.destination, .success)
        XCTAssertNil(model.serverError)
    }

    func test_joinModel_alreadyInvitedGoesToLogin() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(409, ["detail": [["code": "join_request.phone_already_invited"]]])
        }
        let model = JoinModel(client: makeClient())
        model.firstName = "ada"
        model.lastName = "lovelace"
        model.phone = "+15555550100"
        model.email = "ada@pda.test"
        model.smsConsent = true
        model.guidelinesConsent = true
        await model.submit()
        XCTAssertEqual(model.destination, .login)
    }

    func test_loginModel_unknownPhoneOpensJoin() async {
        MockHTTP.handler = { _ in MockHTTP.json(200, ["status": "unknown"]) }
        let model = LoginModel(client: SessionClient(baseURL: base, session: MockHTTP.session(), tokens: MemoryTokenStore()))
        model.phone = "+15555550999"
        await model.submitPhone()
        XCTAssertEqual(model.step, .join)
    }

    private func makeClient() -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session())
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}

private extension URLRequest {
    var json: [String: Any]? {
        guard let httpBody, !httpBody.isEmpty else { return nil }
        return try? JSONSerialization.jsonObject(with: httpBody) as? [String: Any]
    }
}
