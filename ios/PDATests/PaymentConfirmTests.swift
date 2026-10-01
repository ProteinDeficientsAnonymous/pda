import XCTest

@testable import PDA

final class PaymentConfirmTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_eventRequiresPaymentConfirmation_needsPriceAndMethod() throws {
        XCTAssertTrue(eventRequiresPaymentConfirmation(try paid(venmo: "@host")))
        XCTAssertTrue(eventRequiresPaymentConfirmation(try paid(venmo: "", cashapp: "$host")))
        XCTAssertTrue(eventRequiresPaymentConfirmation(try paid(venmo: "", zelle: "host@example.com")))
        XCTAssertFalse(eventRequiresPaymentConfirmation(try paid(price: "", venmo: "@host")))
        XCTAssertFalse(eventRequiresPaymentConfirmation(try paid(price: "   ", venmo: "@host")))
        XCTAssertFalse(eventRequiresPaymentConfirmation(try paid(venmo: "  ")))
        XCTAssertFalse(eventRequiresPaymentConfirmation(try paid(venmo: "", cashapp: "", zelle: "")))
    }

    func test_needsPaymentConfirmation_respectsFlagStatusAndPriorConfirm() throws {
        let event = try paid(venmo: "@host")
        XCTAssertFalse(needsPaymentConfirmation(event: event, flagOn: false, status: "attending", alreadyPaid: false))
        XCTAssertTrue(needsPaymentConfirmation(event: event, flagOn: true, status: "attending", alreadyPaid: false))
        XCTAssertFalse(needsPaymentConfirmation(event: event, flagOn: true, status: "maybe", alreadyPaid: false))
        XCTAssertFalse(needsPaymentConfirmation(event: event, flagOn: true, status: "cant_go", alreadyPaid: false))
        XCTAssertFalse(needsPaymentConfirmation(event: event, flagOn: true, status: "attending", alreadyPaid: true))
        let confirmed = try paid(venmo: "@host", alreadyPaid: true)
        XCTAssertFalse(memberRsvpNeedsPayment(event: confirmed, flagOn: true, status: "attending"))
        XCTAssertTrue(memberRsvpNeedsPayment(event: event, flagOn: true, status: "attending"))
    }

    func test_paymentLinks_matchWeb() {
        XCTAssertEqual(formatPaymentPrice("10"), "$10")
        XCTAssertEqual(formatPaymentPrice("$10"), "$10")
        XCTAssertEqual(formatPaymentPrice("sliding scale"), "sliding scale")
        XCTAssertEqual(venmoPayURL("@host")?.absoluteString, "https://venmo.com/u/host")
        XCTAssertEqual(venmoPayURL("https://venmo.com/u/host")?.absoluteString, "https://venmo.com/u/host")
        XCTAssertEqual(cashAppPayURL("$host", price: "10")?.absoluteString, "https://cash.app/$host/10")
        XCTAssertEqual(cashAppPayURL("$host", price: "sliding scale")?.absoluteString, "https://cash.app/$host")
        XCTAssertEqual(paymentZelleLine("host@example.com"), "zelle: host@example.com")
        XCTAssertNil(venmoPayURL("  "))
    }

    func test_paymentConfirmCopy_isLowercase() {
        let lines = [
            PaymentConfirmCopy.instructions,
            PaymentConfirmCopy.confirm,
            PaymentConfirmCopy.back,
            PaymentConfirmCopy.venmo,
            PaymentConfirmCopy.cashapp,
            PaymentConfirmCopy.required,
        ]
        XCTAssertEqual(lines, lines.map { $0.lowercased() })
        XCTAssertEqual(PaymentConfirmCopy.instructions, "pay the host before you rsvp — then confirm below")
        XCTAssertEqual(PaymentConfirmCopy.confirm, "yes, i paid")
        XCTAssertEqual(PaymentConfirmCopy.back, "back")
        XCTAssertEqual(PaymentConfirmCopy.required, "confirm you paid before rsvping to this event")
    }

    func test_publicRsvp_holdsAttendingUntilPaidWhenFlagOn() async throws {
        var posts = 0
        MockHTTP.handler = { request in
            if request.httpMethod == "POST" {
                posts += 1
                let body = try JSONDecoder().decode(PaidFlag.self, from: request.httpBody ?? Data())
                XCTAssertEqual(routePath(request.url), "/api/community/public/events/evt-1/rsvp/")
                XCTAssertTrue(body.paidConfirmed)
                XCTAssertEqual(body.status, "attending")
                return MockHTTP.json(200, ["rsvp_token": "tok"])
            }
            return MockHTTP.json(200, ["flags": ["event_payment_confirmation": true]])
        }
        let model = PublicRsvpModel(eventId: "evt-1", client: publicClient())
        await model.loadPaymentFlag()
        model.phone = "+15555550100"
        model.firstName = "ada"
        model.email = "ada@pda.test"
        model.status = "attending"
        model.step = .form
        await model.requestSubmit(event: try paid(venmo: "@host"))
        XCTAssertEqual(posts, 0)
        XCTAssertEqual(model.step, .payment)
        await model.confirmPayment()
        XCTAssertEqual(posts, 1)
        XCTAssertEqual(model.step, .saved)
    }

    func test_publicRsvp_skipsPaymentWhenFlagOffOrMaybe() async throws {
        var paidFlags: [Bool] = []
        MockHTTP.handler = { request in
            if request.httpMethod == "GET" {
                return MockHTTP.json(200, ["flags": ["event_payment_confirmation": false]])
            }
            let body = try JSONDecoder().decode(PaidFlag.self, from: request.httpBody ?? Data())
            paidFlags.append(body.paidConfirmed)
            return MockHTTP.json(200, ["rsvp_token": "tok"])
        }
        let model = PublicRsvpModel(eventId: "evt-1", client: publicClient())
        await model.loadPaymentFlag()
        model.firstName = "ada"
        model.email = "ada@pda.test"
        model.status = "attending"
        model.step = .form
        await model.requestSubmit(event: try paid(venmo: "@host"))
        XCTAssertEqual(model.step, .saved)
        XCTAssertEqual(paidFlags, [false])

        let maybe = PublicRsvpModel(eventId: "evt-1", client: publicClient())
        maybe.flagOn = true
        maybe.firstName = "ada"
        maybe.email = "ada@pda.test"
        maybe.status = "maybe"
        maybe.step = .form
        await maybe.requestSubmit(event: try paid(venmo: "@host"))
        XCTAssertEqual(maybe.step, .saved)
        XCTAssertEqual(paidFlags, [false, false])
    }

    func test_publicRsvp_skipShowsBackendError() async throws {
        MockHTTP.handler = { _ in
            MockHTTP.json(400, ["detail": [["code": "event.payment_confirmation_required"]]])
        }
        let model = PublicRsvpModel(eventId: "evt-1", client: publicClient())
        model.step = .form
        model.firstName = "ada"
        model.email = "ada@pda.test"
        model.status = "attending"
        await model.confirmPayment()
        XCTAssertEqual(model.error, PaymentConfirmCopy.required)
        XCTAssertEqual(model.step, .form)
    }

    func test_memberRsvp_postsPaidConfirmedAndMapsSkip() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(routePath(request.url), "/api/community/events/evt-1/rsvp/")
            let obj = try JSONSerialization.jsonObject(with: request.httpBody ?? Data()) as! [String: Any]
            if obj.keys.contains("paid_confirmed") {
                let body = try JSONDecoder().decode(PaidFlag.self, from: request.httpBody ?? Data())
                XCTAssertTrue(body.paidConfirmed)
                return MockHTTP.json(200, ["id": "evt-1", "title": "potluck", "my_rsvp": "attending"])
            }
            return MockHTTP.json(400, ["detail": [["code": "event.payment_confirmation_required"]]])
        }
        let client = EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
        do {
            _ = try await client.setRsvp(eventId: "evt-1", status: "attending", answers: [:])
            XCTFail("expected payment confirmation")
        } catch {
            XCTAssertEqual(rsvpSaveError(error), PaymentConfirmCopy.required)
        }
        let saved = try await client.setRsvp(
            eventId: "evt-1",
            status: "attending",
            answers: [:],
            paidConfirmed: true
        )
        XCTAssertEqual(saved.myRsvp, "attending")
    }

    func test_publicRsvp_backLeavesTheForm() throws {
        let model = PublicRsvpModel(eventId: "evt-1", client: publicClient())
        model.step = .payment
        model.backFromPayment()
        XCTAssertEqual(model.step, .form)
    }

    private func paid(
        price: String = "10",
        venmo: String = "",
        cashapp: String = "",
        zelle: String = "",
        alreadyPaid: Bool = false
    ) throws -> Event {
        try Event.decodeJSON("""
        {
          "id": "evt-1",
          "title": "potluck",
          "price": "\(price)",
          "venmo_link": "\(venmo)",
          "cashapp_link": "\(cashapp)",
          "zelle_info": "\(zelle)",
          "my_paid_confirmed": \(alreadyPaid)
        }
        """)
    }

    private func publicClient() -> PublicRsvpClient {
        let defaults = UserDefaults(suiteName: "pda-pay-\(UUID().uuidString)")!
        return PublicRsvpClient(
            baseURL: base,
            session: MockHTTP.session(),
            tokens: RsvpTokenStore(defaults: defaults)
        )
    }
}

private struct PaidFlag: Decodable {
    let paidConfirmed: Bool
    let status: String

    enum CodingKeys: String, CodingKey {
        case paidConfirmed = "paid_confirmed"
        case status
    }
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
