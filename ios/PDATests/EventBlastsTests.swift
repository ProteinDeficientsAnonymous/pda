import XCTest

@testable import PDA

final class EventBlastsTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_groupText_getsRecipientsWithBearerAndDefaultsGoingMaybe() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/text-recipients/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, [
                "attending": ["+15551112222"],
                "maybe": ["+15559990000"],
                "cant_go": ["+15553334444"],
                "waitlisted": [],
                "invited": ["+15558887777"],
            ])
        }
        XCTAssertEqual(
            textRecipientsURL(base: base, eventId: "evt-1").absoluteString,
            "https://pda.test/api/community/events/evt-1/text-recipients/"
        )
        let model = GroupTextModel(client: makeClient(tokens), eventId: "evt-1")
        await model.load()
        XCTAssertNil(model.error)
        XCTAssertEqual(model.groups.map(\.label), ["going", "maybe", "can't go", "invited"])
        XCTAssertEqual(model.selected, ["attending", "maybe"])
        XCTAssertEqual(model.phones, ["+15551112222", "+15559990000"])
        XCTAssertEqual(model.smsURI, "sms:/open?addresses=+15551112222,+15559990000")
        XCTAssertEqual(model.selectionLabel, "2 numbers selected")
        XCTAssertEqual(model.copyList, "+15551112222, +15559990000")
        model.toggle("maybe")
        model.toggle("cant_go")
        XCTAssertEqual(model.phones, ["+15551112222", "+15553334444"])
        XCTAssertEqual(model.smsURI, "sms:/open?addresses=+15551112222,+15553334444")
    }

    func test_groupText_403IsThePermissionGate() async {
        var saw = false
        MockHTTP.handler = { request in
            saw = true
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/text-recipients/")
            return MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "get_text_recipients"]]])
        }
        let model = GroupTextModel(client: makeClient(), eventId: "evt-1")
        await model.load()
        XCTAssertTrue(saw)
        XCTAssertEqual(model.error, "couldn't load numbers — try again")
        XCTAssertTrue(model.groups.isEmpty)
        XCTAssertFalse(showsGroupText(userId: "u2", coHostIds: ["u1"], permissions: []))
        XCTAssertTrue(showsGroupText(userId: "u1", coHostIds: ["u1"], permissions: []))
        XCTAssertTrue(showsGroupText(userId: "u2", coHostIds: [], permissions: ["manage_events"]))
    }

    func test_groupText_emptyStateHidesEmptyGroupsAndDedupes() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, [
                "attending": ["+15551112222"],
                "maybe": [],
                "cant_go": [],
                "waitlisted": [],
                "invited": ["+15551112222"],
            ])
        }
        let model = GroupTextModel(client: makeClient(), eventId: "evt-1")
        await model.load()
        XCTAssertEqual(model.groups.map(\.value), ["attending", "invited"])
        model.toggle("invited")
        XCTAssertEqual(model.phones, ["+15551112222"])
        XCTAssertEqual(model.selectionLabel, "1 number selected")
        model.toggle("attending")
        model.toggle("invited")
        XCTAssertEqual(model.phones, [])
        XCTAssertNil(model.smsURI)
        XCTAssertEqual(model.selectionLabel, "no one selected")
        XCTAssertEqual(model.textLabel, "text")
    }

    func test_groupText_nobodyToText() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(200, [
                "attending": [],
                "maybe": [],
                "cant_go": [],
                "waitlisted": [],
                "invited": [],
            ])
        }
        let model = GroupTextModel(client: makeClient(), eventId: "evt-1")
        await model.load()
        XCTAssertEqual(model.empty, "no one has a number to text yet")
        XCTAssertEqual(GroupTextCopy.loading, "loading numbers…")
        XCTAssertEqual(GroupTextCopy.title, "group text")
        XCTAssertEqual(GroupTextCopy.hint, "pick who to message")
        XCTAssertEqual(GroupTextCopy.copy, "copy numbers instead")
        XCTAssertEqual(GroupTextCopy.cancel, "cancel")
        for line in [GroupTextCopy.title, GroupTextCopy.hint, GroupTextCopy.copy, model.empty ?? ""] {
            XCTAssertEqual(line, line.lowercased())
        }
    }

    func test_emailBlast_postsAudienceWithBearerAfterConfirm() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        var posted = false
        MockHTTP.handler = { request in
            posted = true
            XCTAssertEqual(request.httpMethod, "POST")
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/email-blast/")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            let body = try JSONDecoder().decode(EmailBlastBody.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.subject, "schedule update")
            XCTAssertEqual(body.message, "we moved to 6pm")
            XCTAssertEqual(body.audience, ["attending", "maybe", "cant_go"])
            return MockHTTP.json(200, [
                "sent_count": 2,
                "skipped_no_email_count": 1,
                "failed_count": 0,
            ])
        }
        let model = EmailBlastModel(
            client: makeClient(tokens),
            eventId: "evt-1",
            guestStatuses: ["attending", "maybe", "cant_go"]
        )
        model.subject = "schedule update"
        model.message = "we moved to 6pm"
        await model.next()
        XCTAssertFalse(posted)
        XCTAssertTrue(model.confirming)
        XCTAssertEqual(model.confirmBody, "email 3 attendees? this can't be undone — anyone without an email on file will be skipped.")
        await model.send()
        XCTAssertTrue(posted)
        XCTAssertEqual(model.success, "sent to 2 attendees, 1 skipped (no email) 🌱")
    }

    func test_emailBlast_validationAndNarrowedAudience() async throws {
        var posted = false
        MockHTTP.handler = { request in
            posted = true
            let body = try JSONDecoder().decode(EmailBlastBody.self, from: request.httpBody ?? Data())
            XCTAssertEqual(body.audience, ["attending"])
            return MockHTTP.json(200, [
                "sent_count": 1,
                "skipped_no_email_count": 0,
                "failed_count": 0,
            ])
        }
        let blank = EmailBlastModel(client: makeClient(), eventId: "evt-1", guestStatuses: ["attending"])
        blank.message = "hello"
        await blank.next()
        XCTAssertEqual(blank.error, "add a subject")
        XCTAssertFalse(posted)
        blank.subject = "hi"
        blank.message = "   "
        await blank.next()
        XCTAssertEqual(blank.error, "add a message")
        XCTAssertFalse(posted)

        let model = EmailBlastModel(
            client: makeClient(),
            eventId: "evt-1",
            guestStatuses: ["attending", "maybe", "cant_go", "waitlisted"]
        )
        XCTAssertEqual(model.audiences.map(\.label), ["going", "maybe", "can't go", "waitlisted"])
        model.toggle("maybe")
        model.toggle("cant_go")
        model.toggle("waitlisted")
        XCTAssertEqual(model.preview, "emailing 1 attendee — anyone without an email is skipped")
        model.subject = "hi"
        model.message = "going folks only"
        await model.next()
        await model.send()
        XCTAssertTrue(posted)
        XCTAssertEqual(model.success, "sent to 1 attendee 🌱")
        XCTAssertFalse(showsEmailBlast(userId: "u1", coHostIds: ["u1"], permissions: [], status: "draft", guestCount: 2))
        XCTAssertFalse(showsEmailBlast(userId: "u1", coHostIds: ["u1"], permissions: [], status: "active", guestCount: 0))
        XCTAssertTrue(showsEmailBlast(userId: "u1", coHostIds: ["u1"], permissions: [], status: "active", guestCount: 2))
    }

    func test_emailBlast_403AndNoRecipients() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied", "action": "send_email_blast"]]])
        }
        let denied = EmailBlastModel(client: makeClient(), eventId: "evt-1", guestStatuses: ["attending"])
        denied.subject = "hi"
        denied.message = "body"
        denied.confirming = true
        await denied.send()
        XCTAssertEqual(denied.error, "you don't have permission to do that")
        XCTAssertNil(denied.success)

        MockHTTP.handler = { _ in
            MockHTTP.json(400, ["detail": [["code": "event.blast_no_recipients"]]])
        }
        let empty = EmailBlastModel(client: makeClient(), eventId: "evt-1", guestStatuses: ["attending"])
        empty.subject = "hi"
        empty.message = "body"
        empty.confirming = true
        await empty.send()
        XCTAssertEqual(empty.error, "no attendees in that audience have an email — nothing to send")

        MockHTTP.handler = { _ in MockHTTP.json(500, [:]) }
        let failed = EmailBlastModel(client: makeClient(), eventId: "evt-1", guestStatuses: ["attending"])
        failed.subject = "hi"
        failed.message = "body"
        failed.confirming = true
        await failed.send()
        XCTAssertEqual(failed.error, "couldn't send — try again")
    }

    private func makeClient(_ tokens: MemoryTokenStore = MemoryTokenStore()) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }
}

private struct EmailBlastBody: Decodable {
    let subject: String
    let message: String
    let audience: [String]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
