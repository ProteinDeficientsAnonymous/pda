import SwiftUI

struct SmsPolicySection: Equatable {
    let heading: String
    let paragraphs: [String]
    let bullets: [String]
}

// hardcoded: twilio toll-free verification depends on stable content
enum SmsPolicyCopy {
    static let title = "sms policy"
    static let intro =
        "when you join pda and provide your phone number, you consent to receive sms messages related to community events."
    static let sections: [SmsPolicySection] = [
        SmsPolicySection(
            heading: "what we send",
            paragraphs: [],
            bullets: [
                "event invitations and confirmations from event hosts",
                "updates about events you've rsvp'd to (e.g. location changes, reminders, cancellations)",
                "one-time login links when an admin sends you one (for password resets or initial onboarding)",
            ]
        ),
        SmsPolicySection(
            heading: "what we don't send",
            paragraphs: [],
            bullets: [
                "marketing or promotional messages",
                "third-party advertising",
                "automated marketing sequences",
            ]
        ),
        SmsPolicySection(
            heading: "how we got your consent",
            paragraphs: [
                "you provided your phone number when you submitted a join request and checked the box agreeing to receive sms about events. we record the date of consent on your join request.",
            ],
            bullets: []
        ),
        SmsPolicySection(
            heading: "how to opt out",
            paragraphs: [],
            bullets: [
                "reply stop to any message to opt out of all sms from pda. you'll get one final confirmation, then no further messages.",
                "reply m to mute sms for one specific event. you'll stop getting messages about that event but continue to get them about others.",
                "contact a community organizer to remove your phone number entirely.",
            ]
        ),
        SmsPolicySection(
            heading: "frequency",
            paragraphs: [
                "messages are sent only when something happens — an event invite, a host update, etc. there's no scheduled or recurring sms. most members get fewer than 10 messages per month.",
            ],
            bullets: []
        ),
        SmsPolicySection(
            heading: "cost",
            paragraphs: [
                "standard message and data rates from your carrier may apply. pda does not charge for sms.",
            ],
            bullets: []
        ),
        SmsPolicySection(
            heading: "contact",
            paragraphs: [
                "for questions about how we use your phone number, contact a vetting member or admin via the community.",
            ],
            bullets: []
        ),
    ]
}

struct SmsPolicyView: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 24) {
                    Text(SmsPolicyCopy.intro)
                    ForEach(SmsPolicyCopy.sections, id: \.heading) { section in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(section.heading).font(.headline)
                            ForEach(section.paragraphs, id: \.self) { paragraph in
                                Text(paragraph)
                            }
                            ForEach(section.bullets, id: \.self) { bullet in
                                Text("• \(bullet)")
                            }
                        }
                    }
                }
                .font(.subheadline)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding()
            }
            .navigationTitle(SmsPolicyCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton("close", variant: .secondary) { dismiss() }
                }
            }
        }
    }
}
