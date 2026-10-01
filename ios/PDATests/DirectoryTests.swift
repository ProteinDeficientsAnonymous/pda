import XCTest

@testable import PDA

final class DirectoryTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func setUp() {
        super.setUp()
        MockHTTP.handler = nil
    }

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_directoryURLs_keepTrailingSlash() {
        XCTAssertEqual(
            directoryURL(base: base).absoluteString,
            "https://pda.test/api/auth/users/directory/"
        )
        XCTAssertEqual(
            userProfileURL(base: base, userId: "user-1").absoluteString,
            "https://pda.test/api/auth/users/user-1/profile/"
        )
    }

    func test_directory_getsMembersWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/directory/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                [
                    "id": "u-2",
                    "full_name": "Bea",
                    "phone_number": "",
                    "email": "bea@pda.test",
                    "profile_photo_url": "",
                ],
                [
                    "id": "u-1",
                    "full_name": "Ada Lovelace",
                    "phone_number": "+15555550100",
                    "email": "ada@pda.test",
                    "profile_photo_url": "https://pda.test/media/ada.jpg",
                ],
            ])
        }
        let members = try await makeClient(tokens).directory()
        XCTAssertEqual(members.map(\.id), ["u-2", "u-1"])
        XCTAssertEqual(members[1].fullName, "Ada Lovelace")
        XCTAssertEqual(members[1].phoneNumber, "+15555550100")
        XCTAssertEqual(members[1].email, "ada@pda.test")
        XCTAssertEqual(members[1].profilePhotoUrl, "https://pda.test/media/ada.jpg")
        XCTAssertEqual(directorySubtitle(phone: members[1].phoneNumber, email: members[1].email), "+15555550100")
        XCTAssertEqual(directorySubtitle(phone: members[0].phoneNumber, email: members[0].email), "bea@pda.test")
        XCTAssertEqual(directoryInitials(members[1].fullName), "ad")
        XCTAssertEqual(directoryInitials(""), "?")
    }

    func test_directory_403IsForbiddenNotAList() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(routePath(request.url), "/api/auth/users/directory/")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied", "field": NSNull()]]])
        }
        do {
            _ = try await makeClient().directory()
            XCTFail("403 should not return the list")
        } catch DirectoryError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_directoryModel_forbiddenShowsExplanationNotMembers() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = DirectoryModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.members.isEmpty)
        XCTAssertEqual(model.explanationTitle, MemberLockCopy.directoryTitle)
        XCTAssertEqual(model.explanationBody, MemberLockCopy.directoryBody)
    }

    func test_memberProfile_getsProfileWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/auth/users/u-1/profile/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "id": "u-1",
                "full_name": "Ada Lovelace",
                "nickname": "Birdie",
                "phone_number": "",
                "email": "ada@pda.test",
                "bio": "vegan potlucks",
                "pronouns": "she/her",
                "birthday": ["month": 12, "day": 10, "year": 1815],
                "profile_photo_url": "",
                "login_link_requested": false,
            ])
        }
        let profile = try await makeClient(tokens).memberProfile(id: "u-1")
        XCTAssertEqual(profile.name, "Ada Lovelace")
        XCTAssertEqual(profile.nickname, "Birdie")
        XCTAssertEqual(profile.pronouns, "she/her")
        XCTAssertEqual(profile.bio, "vegan potlucks")
        XCTAssertEqual(profile.email, "ada@pda.test")
        XCTAssertEqual(profile.phoneNumber, "")
        XCTAssertEqual(profile.birthday, Birthday(month: 12, day: 10, year: 1815))
        XCTAssertEqual(profileContactLines(profile), ["ada@pda.test"])
        XCTAssertEqual(profileDisplayName(profile), "Ada Lovelace")
    }

    func test_memberProfile_403IsForbidden() async {
        MockHTTP.handler = { request in
            XCTAssertEqual(routePath(request.url), "/api/auth/users/u-1/profile/")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().memberProfile(id: "u-1")
            XCTFail("403 should not return a profile")
        } catch DirectoryError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_profileContactLines_hiddenWhenBothEmpty() {
        let hidden = MemberProfile(
            id: "u-1",
            name: "",
            bio: "",
            pronouns: "",
            nickname: "",
            phoneNumber: "",
            email: "",
            birthday: nil,
            profilePhotoUrl: ""
        )
        XCTAssertEqual(profileContactLines(hidden), [DirectoryCopy.contactHidden])
        XCTAssertEqual(profileDisplayName(hidden), DirectoryCopy.fallbackName)
    }

    func test_filterDirectory_matchesNameEmailOrPhone() {
        let members = [
            DirectoryMember(id: "1", fullName: "Ada Lovelace", phoneNumber: "+15555550100", email: "ada@pda.test", profilePhotoUrl: ""),
            DirectoryMember(id: "2", fullName: "Bea", phoneNumber: "", email: "bea@pda.test", profilePhotoUrl: ""),
        ]
        XCTAssertEqual(filterDirectory(members, query: "  ADA ").map(\.id), ["1"])
        XCTAssertEqual(filterDirectory(members, query: "555").map(\.id), ["1"])
        XCTAssertEqual(filterDirectory(members, query: "bea@").map(\.id), ["2"])
        XCTAssertEqual(filterDirectory(members, query: "").map(\.id), ["1", "2"])
        XCTAssertEqual(directoryEmptyMessage(total: 0, query: ""), DirectoryCopy.empty)
        XCTAssertEqual(directoryEmptyMessage(total: 2, query: "zzz"), "no one matches \"zzz\" 🌿")
    }

    func test_directoryCopy_isLowercase() {
        let blobs = [
            DirectoryCopy.title,
            DirectoryCopy.search,
            DirectoryCopy.loading,
            DirectoryCopy.error,
            DirectoryCopy.empty,
            DirectoryCopy.profileError,
            DirectoryCopy.contactHidden,
            DirectoryCopy.bio,
            DirectoryCopy.fallbackName,
            MemberLockCopy.directoryTitle,
            MemberLockCopy.directoryBody,
        ]
        XCTAssertEqual(DirectoryCopy.title, "members")
        XCTAssertEqual(DirectoryCopy.search, "search name, email, or phone")
        XCTAssertEqual(DirectoryCopy.error, "couldn't load members — try refreshing")
        XCTAssertEqual(DirectoryCopy.profileError, "couldn't load this profile — try again")
        XCTAssertEqual(DirectoryCopy.contactHidden, "contact info hidden")
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
