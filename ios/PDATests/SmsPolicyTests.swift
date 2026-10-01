import XCTest

@testable import PDA

final class SmsPolicyTests: XCTestCase {
    func test_smsPolicyCopy_matchesWebAndIsLowercase() {
        XCTAssertEqual(SmsPolicyCopy.title, "sms policy")
        XCTAssertEqual(
            SmsPolicyCopy.intro,
            "when you join pda and provide your phone number, you consent to receive sms messages related to community events."
        )
        XCTAssertEqual(
            SmsPolicyCopy.sections.map(\.heading),
            [
                "what we send",
                "what we don't send",
                "how we got your consent",
                "how to opt out",
                "frequency",
                "cost",
                "contact",
            ]
        )
        XCTAssertEqual(
            SmsPolicyCopy.sections[0].bullets,
            [
                "event invitations and confirmations from event hosts",
                "updates about events you've rsvp'd to (e.g. location changes, reminders, cancellations)",
                "one-time login links when an admin sends you one (for password resets or initial onboarding)",
            ]
        )
        XCTAssertEqual(SmsPolicyCopy.sections[0].paragraphs, [])
        XCTAssertEqual(
            SmsPolicyCopy.sections[1].bullets,
            [
                "marketing or promotional messages",
                "third-party advertising",
                "automated marketing sequences",
            ]
        )
        XCTAssertEqual(
            SmsPolicyCopy.sections[2].paragraphs,
            [
                "you provided your phone number when you submitted a join request and checked the box agreeing to receive sms about events. we record the date of consent on your join request.",
            ]
        )
        XCTAssertEqual(SmsPolicyCopy.sections[2].bullets, [])
        XCTAssertEqual(
            SmsPolicyCopy.sections[3].bullets,
            [
                "reply stop to any message to opt out of all sms from pda. you'll get one final confirmation, then no further messages.",
                "reply m to mute sms for one specific event. you'll stop getting messages about that event but continue to get them about others.",
                "contact a community organizer to remove your phone number entirely.",
            ]
        )
        XCTAssertEqual(
            SmsPolicyCopy.sections[4].paragraphs,
            [
                "messages are sent only when something happens — an event invite, a host update, etc. there's no scheduled or recurring sms. most members get fewer than 10 messages per month.",
            ]
        )
        XCTAssertEqual(
            SmsPolicyCopy.sections[5].paragraphs,
            ["standard message and data rates from your carrier may apply. pda does not charge for sms."]
        )
        XCTAssertEqual(
            SmsPolicyCopy.sections[6].paragraphs,
            [
                "for questions about how we use your phone number, contact a vetting member or admin via the community.",
            ]
        )
        let blobs = [SmsPolicyCopy.title, SmsPolicyCopy.intro]
            + SmsPolicyCopy.sections.flatMap { [$0.heading] + $0.paragraphs + $0.bullets }
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }
}
