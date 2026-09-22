import XCTest

@testable import PDA

final class AdminMemberDetailTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func setUp() {
        super.setUp()
        MockHTTP.handler = nil
    }

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_adminMemberDetail_getsMatchingUserFromMembersList() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                adminMemberJSON(id: "u-1", name: "Bea", phone: "+15555550101", email: "bea@pda.test", bio: ""),
                adminMemberJSON(id: "u-2", name: "Ada Lovelace", phone: "+15555550100", email: "ada@pda.test", bio: "vegan potlucks"),
            ])
        }
        let member = try await makeClient(tokens).adminMemberDetail(id: "u-2")
        XCTAssertEqual(member.id, "u-2")
        XCTAssertEqual(member.fullName, "Ada Lovelace")
        XCTAssertEqual(member.phoneNumber, "+15555550100")
        XCTAssertEqual(member.email, "ada@pda.test")
        XCTAssertEqual(member.bio, "vegan potlucks")
        XCTAssertEqual(adminMemberDetailTitle(member), "Ada Lovelace")
    }

    func test_adminMemberDetail_403WithoutManageUsers() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().adminMemberDetail(id: "u-1")
            XCTFail("403 should not return a member")
        } catch AdminMembersError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminMemberDetail_missingUserIsNotFound() async throws {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, [
                adminMemberJSON(id: "u-1", name: "Bea", phone: "", email: "", bio: ""),
            ])
        }
        do {
            _ = try await makeClient().adminMemberDetail(id: "missing")
            XCTFail("missing member should not return")
        } catch AdminMembersError.notFound {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_adminMemberDetailModel_forbiddenShowsExplanationNotMember() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AdminMemberDetailModel(client: makeClient())
        await model.load(id: "u-1")
        XCTAssertTrue(model.forbidden)
        XCTAssertNil(model.member)
        XCTAssertEqual(model.explanationTitle, AdminMembersCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, AdminMembersCopy.forbiddenBody)
    }

    func test_adminMemberDetailCopy_isLowercase() {
        let blobs = [
            AdminMemberDetailCopy.notFound,
            AdminMemberDetailCopy.error,
            AdminMemberDetailCopy.bio,
        ]
        XCTAssertEqual(AdminMemberDetailCopy.notFound, "member not found")
        XCTAssertEqual(AdminMemberDetailCopy.error, "couldn't load members — try refreshing")
        XCTAssertEqual(AdminMemberDetailCopy.bio, "bio")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private func adminMemberJSON(id: String, name: String, phone: String, email: String, bio: String) -> [String: Any] {
    [
        "id": id,
        "full_name": name,
        "phone_number": phone,
        "email": email,
        "bio": bio,
        "date_joined": "2026-01-01T00:00:00Z",
        "roles": [],
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
