import XCTest

@testable import PDA

final class BulkCreateTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_bulkMemberPhones_matchesWebNormalize() {
        XCTAssertEqual(
            bulkMemberPhones("555-123-4567\n\n  +44 20 7946 0958  \n15551230001\n12\n"),
            ["+15551234567", "+44 20 7946 0958", "+15551230001", "+12"]
        )
        XCTAssertEqual(bulkMemberPhones("   \n"), [])
    }

    func test_submitBulk_emptyDoesNotPost() async {
        MockHTTP.handler = { _ in
            XCTFail("empty list must not post")
            return MockHTTP.json(500, [:])
        }
        let model = BulkCreateModel(client: makeClient())
        model.raw = "  \n"
        await model.submit()
        XCTAssertEqual(model.formError, "add at least one phone number")
        XCTAssertNil(model.response)
    }

    func test_submitBulk_postsPhoneNumbers() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/auth/bulk-create-users/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let obj = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as! [String: Any]
            XCTAssertEqual(Set(obj.keys), Set(["phone_numbers"]))
            let body = try JSONDecoder().decode(BulkPhonesBody.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.phone_numbers, ["+15551234567", "+not-a-phone"])
            return MockHTTP.json(200, [
                "created": 1,
                "failed": 1,
                "results": [
                    [
                        "row": 1,
                        "phone_number": "+15551234567",
                        "success": true,
                        "magic_link_token": "magic-1",
                    ],
                    [
                        "row": 2,
                        "phone_number": "not-a-phone",
                        "success": false,
                        "error": "phone.invalid",
                    ],
                ],
            ])
        }
        let model = BulkCreateModel(client: makeClient(tokens))
        model.raw = "555-123-4567\n+not-a-phone"
        await model.submit()
        XCTAssertNil(model.formError)
        XCTAssertEqual(model.response?.created, 1)
        XCTAssertEqual(model.response?.failed, 1)
        XCTAssertEqual(
            bulkResultsSummary(created: 1, failed: 1),
            "created 1 of 2 — share each magic link with its recipient; links won't be shown again."
        )
        let link = bulkResultLink(base: base, token: "magic-1")
        XCTAssertEqual(link, "https://pda.test/magic-login/magic-1")
        XCTAssertEqual(
            bulkResultSMS(phone: "+15551234567", url: link),
            memberSmsLink(phone: "+15551234567", message: memberWelcomeMessage(firstName: "", url: link))
        )
        XCTAssertEqual(bulkFailureLine(phone: "not-a-phone", error: "phone.invalid"), "not-a-phone — phone.invalid")
        XCTAssertEqual(bulkFailureLine(phone: "555", error: nil), "555 — unknown error")
        model.copy(row: 1)
        XCTAssertEqual(model.copyLabel(row: 1), "copied ✓")
        XCTAssertEqual(model.copyLabel(row: 2), "copy link")
    }

    func test_submitBulk_403WithoutManageUsers() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/auth/bulk-create-users/")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "bulk_create_users"]]])
        }
        let model = BulkCreateModel(client: makeClient())
        model.raw = "555-123-4567"
        await model.submit()
        XCTAssertNil(model.response)
        XCTAssertEqual(model.formError, "you don't have permission to do that")
    }

    func test_submitBulk_unknownFailureUsesFallback() async {
        MockHTTP.handler = { _ in MockHTTP.json(500, [:]) }
        let model = BulkCreateModel(client: makeClient())
        model.raw = "555-123-4567"
        await model.submit()
        XCTAssertNil(model.response)
        XCTAssertEqual(model.formError, "couldn't create members — try again")
    }

    func test_bulkCreateCopy_isLowercase() {
        let blobs = [
            BulkCreateCopy.button,
            BulkCreateCopy.title,
            BulkCreateCopy.phoneNumbers,
            BulkCreateCopy.hint,
            BulkCreateCopy.placeholder,
            BulkCreateCopy.cancel,
            BulkCreateCopy.create,
            BulkCreateCopy.creating,
            BulkCreateCopy.empty,
            BulkCreateCopy.failure,
            BulkCreateCopy.forbidden,
            BulkCreateCopy.resultsTitle,
            BulkCreateCopy.created,
            BulkCreateCopy.failed,
            BulkCreateCopy.copyLink,
            BulkCreateCopy.copied,
            BulkCreateCopy.sendWelcome,
            BulkCreateCopy.done,
            BulkCreateCopy.unknownError,
        ]
        XCTAssertEqual(BulkCreateCopy.button, "bulk add")
        XCTAssertEqual(BulkCreateCopy.title, "bulk add members")
        XCTAssertEqual(BulkCreateCopy.phoneNumbers, "phone numbers")
        XCTAssertEqual(
            BulkCreateCopy.hint,
            "one per line — us numbers assumed unless prefixed with + and a country code"
        )
        XCTAssertEqual(BulkCreateCopy.placeholder, "555-123-4567\n+44 20 7946 0958")
        XCTAssertEqual(BulkCreateCopy.cancel, "cancel")
        XCTAssertEqual(BulkCreateCopy.create, "create members")
        XCTAssertEqual(BulkCreateCopy.creating, "creating…")
        XCTAssertEqual(BulkCreateCopy.empty, "add at least one phone number")
        XCTAssertEqual(BulkCreateCopy.failure, "couldn't create members — try again")
        XCTAssertEqual(BulkCreateCopy.forbidden, "you don't have permission to do that")
        XCTAssertEqual(BulkCreateCopy.resultsTitle, "bulk results")
        XCTAssertEqual(BulkCreateCopy.created, "created")
        XCTAssertEqual(BulkCreateCopy.failed, "failed")
        XCTAssertEqual(BulkCreateCopy.copyLink, "copy link")
        XCTAssertEqual(BulkCreateCopy.copied, "copied ✓")
        XCTAssertEqual(BulkCreateCopy.sendWelcome, "send welcome message")
        XCTAssertEqual(BulkCreateCopy.done, "done")
        XCTAssertEqual(BulkCreateCopy.unknownError, "unknown error")
        XCTAssertEqual(
            bulkCreateURL(base: base).absoluteString,
            "https://pda.test/api/auth/bulk-create-users/"
        )
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private struct BulkPhonesBody: Decodable {
    let phone_numbers: [String]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
