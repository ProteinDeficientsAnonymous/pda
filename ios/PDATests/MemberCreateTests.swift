import XCTest

@testable import PDA

final class MemberCreateTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_createMemberURL_keepsTrailingSlash() {
        let url = createMemberURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/auth/create-user/")
        XCTAssertNil(url.query)
    }

    func test_createMember_postsTrimmedFieldsAndOmitsEmptyLastName() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/auth/create-user/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body, [
                "phone_number": "+12025550101",
                "email": "ada@example.com",
                "first_name": "Ada",
            ])
            return MockHTTP.json(201, [
                "id": "u1",
                "phone_number": "+12025550101",
                "first_name": "Ada",
                "full_name": "Ada",
                "magic_link_token": "tok",
            ])
        }
        let created = try await makeClient(tokens).createMember(
            firstName: "  Ada  ",
            lastName: "   ",
            phone: "  +12025550101  ",
            email: "  ada@example.com  "
        )
        XCTAssertEqual(created.id, "u1")
        XCTAssertEqual(created.magicLinkToken, "tok")
        XCTAssertEqual(created.firstName, "Ada")
        XCTAssertEqual(created.fullName, "Ada")
        XCTAssertEqual(created.phoneNumber, "+12025550101")
    }

    func test_createMember_includesLastNameWhenPresent() async throws {
        MockHTTP.handler = { request in
            let body = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as? [String: String]
            XCTAssertEqual(body?["last_name"], "Lovelace")
            XCTAssertNil(body?["role_id"])
            return MockHTTP.json(201, [
                "id": "u2",
                "phone_number": "+12025550101",
                "first_name": "Ada",
                "full_name": "Ada Lovelace",
                "magic_link_token": "tok",
            ])
        }
        _ = try await makeClient().createMember(
            firstName: "Ada",
            lastName: " Lovelace ",
            phone: "+12025550101",
            email: "ada@example.com"
        )
    }

    func test_createMember_403ShowsExplanation() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().createMember(
                firstName: "Ada",
                lastName: "",
                phone: "+12025550101",
                email: "ada@example.com"
            )
            XCTFail("403 should not create")
        } catch MemberCreateError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
        let model = MemberCreateModel(client: makeClient())
        model.firstName = "Ada"
        model.phone = "+12025550101"
        model.email = "ada@example.com"
        let created = await model.submit()
        XCTAssertFalse(created)
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.created)
        XCTAssertEqual(model.explanationTitle, MemberCreateCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, "you need permission to create users to add a member.")
    }

    func test_createMember_serverFailureShowsTryAgain() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(500, ["detail": "nope"])
        }
        let model = MemberCreateModel(client: makeClient())
        model.firstName = "Ada"
        model.phone = "+12025550101"
        model.email = "ada@example.com"
        let created = await model.submit()
        XCTAssertFalse(created)
        XCTAssertFalse(model.forbidden)
        XCTAssertEqual(model.formError, "couldn't create member — try again")
    }

    func test_createMember_clientValidationSkipsPost() async {
        var posted = false
        MockHTTP.handler = { _ in
            posted = true
            return MockHTTP.json(201, [:])
        }
        let missingFirst = MemberCreateModel(client: makeClient())
        missingFirst.phone = "+12025550101"
        missingFirst.email = "ada@example.com"
        let missingFirstCreated = await missingFirst.submit()
        XCTAssertFalse(missingFirstCreated)
        XCTAssertEqual(missingFirst.formError, "first name is required")

        let missingPhone = MemberCreateModel(client: makeClient())
        missingPhone.firstName = "Ada"
        missingPhone.email = "ada@example.com"
        let missingPhoneCreated = await missingPhone.submit()
        XCTAssertFalse(missingPhoneCreated)
        XCTAssertEqual(missingPhone.formError, "phone number is required")

        let missingEmail = MemberCreateModel(client: makeClient())
        missingEmail.firstName = "Ada"
        missingEmail.phone = "+12025550101"
        let missingEmailCreated = await missingEmail.submit()
        XCTAssertFalse(missingEmailCreated)
        XCTAssertEqual(missingEmail.formError, "email is required")
        XCTAssertFalse(posted)
    }

    func test_welcomeDialog_usesOriginCopyAndSms() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(201, [
                "id": "u1",
                "phone_number": "+12025550101",
                "first_name": "Ada",
                "full_name": "Ada Lovelace",
                "magic_link_token": "tok",
            ])
        }
        let model = MemberCreateModel(client: makeClient())
        model.firstName = "Ada"
        model.phone = "+12025550101"
        model.email = "ada@example.com"
        let created = await model.submit()
        XCTAssertTrue(created)
        XCTAssertEqual(model.welcomeTitle, "welcome ada lovelace")
        XCTAssertEqual(model.welcomeBody, "share this one-time login link; it won't be shown again.")
        XCTAssertEqual(model.magicLink, "https://pda.test/magic-login/tok")
        XCTAssertEqual(model.copyLabel, "copy link")
        model.copyLink()
        XCTAssertEqual(model.copyLabel, "copied ✓")
        XCTAssertEqual(
            memberWelcomeMessage(firstName: "Ada", url: model.magicLink),
            "hi ada 🌱 welcome to pda! use this link to sign in: https://pda.test/magic-login/tok"
        )
        XCTAssertEqual(
            memberWelcomeMessage(firstName: "  ", url: model.magicLink),
            "hi 🌱 welcome to pda! use this link to sign in: https://pda.test/magic-login/tok"
        )
        XCTAssertTrue(model.smsLink.hasPrefix("sms:+12025550101&body="))
        XCTAssertFalse(model.smsLink.contains("?body="))
        XCTAssertTrue(model.smsLink.contains("hi%20ada"))
        XCTAssertTrue(model.smsLink.contains("%3A%2F%2Fpda.test%2Fmagic-login%2Ftok"))
    }

    func test_welcomeTitle_usesFormattedPhoneWhenNameMissing() {
        XCTAssertEqual(
            memberWelcomeTitle(fullName: "", phone: "+12025550101"),
            "welcome (202) 555-0101"
        )
        XCTAssertEqual(
            memberWelcomeTitle(fullName: "Ada", phone: "+12025550101"),
            "welcome ada"
        )
    }

    func test_done_closesAndClearsForm() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(201, [
                "id": "u1",
                "phone_number": "+12025550101",
                "first_name": "",
                "full_name": "",
                "magic_link_token": "tok",
            ])
        }
        let model = MemberCreateModel(client: makeClient())
        model.firstName = "Ada"
        model.lastName = "Lovelace"
        model.phone = "+12025550101"
        model.email = "ada@example.com"
        _ = await model.submit()
        model.copyLink()
        model.done()
        XCTAssertTrue(model.closed)
        XCTAssertEqual(model.firstName, "")
        XCTAssertEqual(model.lastName, "")
        XCTAssertEqual(model.phone, "")
        XCTAssertEqual(model.email, "")
        XCTAssertNil(model.formError)
        XCTAssertNil(model.created)
        XCTAssertFalse(model.copied)
        XCTAssertEqual(model.copyLabel, "copy link")
    }

    func test_addMemberButton_onlyOnMembersTab() {
        XCTAssertTrue(showsAddMemberButton(tab: "members"))
        XCTAssertFalse(showsAddMemberButton(tab: "non-members"))
        XCTAssertFalse(showsAddMemberButton(tab: "roles"))
        XCTAssertEqual(MemberCreateCopy.button, "add member")
        XCTAssertEqual(MemberCreateCopy.title, "add member")
    }

    func test_memberCreateCopy_isLowercase() {
        let blobs = [
            MemberCreateCopy.button,
            MemberCreateCopy.title,
            MemberCreateCopy.firstName,
            MemberCreateCopy.lastName,
            MemberCreateCopy.phone,
            MemberCreateCopy.email,
            MemberCreateCopy.cancel,
            MemberCreateCopy.create,
            MemberCreateCopy.creating,
            MemberCreateCopy.welcomeBody,
            MemberCreateCopy.copyLink,
            MemberCreateCopy.copied,
            MemberCreateCopy.sendWelcome,
            MemberCreateCopy.done,
            MemberCreateCopy.firstNameRequired,
            MemberCreateCopy.phoneRequired,
            MemberCreateCopy.emailRequired,
            MemberCreateCopy.failure,
            MemberCreateCopy.forbiddenTitle,
            MemberCreateCopy.forbiddenBody,
        ]
        XCTAssertEqual(MemberCreateCopy.copied, "copied ✓")
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
