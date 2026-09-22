import SwiftUI

enum GroupTextCopy {
    static let title = "group text"
    static let loading = "loading numbers…"
    static let loadError = "couldn't load numbers — try again"
    static let hint = "pick who to message"
    static let empty = "no one has a number to text yet"
    static let none = "no one selected"
    static let copy = "copy numbers instead"
    static let copied = "copied"
    static let cancel = "cancel"
    static let text = "text"
}

enum EmailBlastCopy {
    static let title = "email blast"
    static let subject = "subject"
    static let message = "message"
    static let sendTo = "send to"
    static let subjectRequired = "add a subject"
    static let messageRequired = "add a message"
    static let cancel = "cancel"
    static let next = "next"
    static let back = "back"
    static let send = "send"
    static let sending = "sending…"
    static let confirmTitle = "send email blast?"
    static let forbidden = "you don't have permission to do that"
    static let noRecipients = "no attendees in that audience have an email — nothing to send"
    static let invalidAudience = "that audience choice is not valid"
    static let failure = "couldn't send — try again"
    static let done = "done"
}

struct TextRecipients: Decodable, Equatable {
    var attending: [String] = []
    var maybe: [String] = []
    var cantGo: [String] = []
    var waitlisted: [String] = []
    var invited: [String] = []

    enum CodingKeys: String, CodingKey {
        case attending, maybe, waitlisted, invited
        case cantGo = "cant_go"
    }

    func phones(_ key: String) -> [String] {
        switch key {
        case "attending": attending
        case "maybe": maybe
        case "cant_go": cantGo
        case "waitlisted": waitlisted
        case "invited": invited
        default: []
        }
    }
}

struct GroupTextOption: Equatable, Identifiable {
    var value: String
    var label: String
    var count: Int
    var id: String { value }
}

private let groupTextGroups: [(String, String)] = [
    ("attending", "going"),
    ("maybe", "maybe"),
    ("cant_go", "can't go"),
    ("waitlisted", "waitlisted"),
    ("invited", "invited"),
]

private let emailBlastGroups: [(String, String)] = [
    ("attending", "going"),
    ("maybe", "maybe"),
    ("cant_go", "can't go"),
    ("waitlisted", "waitlisted"),
]

func textRecipientsURL(base: URL, eventId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/text-recipients/", relativeTo: base)!.absoluteURL
}

func emailBlastURL(base: URL, eventId: String) -> URL {
    URL(string: "/api/community/events/\(eventId)/email-blast/", relativeTo: base)!.absoluteURL
}

func showsGroupText(userId: String?, coHostIds: [String], permissions: [String]) -> Bool {
    guard let userId else { return false }
    return coHostIds.contains(userId) || permissions.contains("manage_events")
}

func showsEmailBlast(
    userId: String?,
    coHostIds: [String],
    permissions: [String],
    status: String,
    guestCount: Int
) -> Bool {
    showsGroupText(userId: userId, coHostIds: coHostIds, permissions: permissions)
        && status != "draft"
        && guestCount > 0
}

func groupTextPhones(_ recipients: TextRecipients, selected: [String]) -> [String] {
    var phones: [String] = []
    var seen = Set<String>()
    for key in selected {
        for phone in recipients.phones(key) where seen.insert(phone).inserted {
            phones.append(phone)
        }
    }
    return phones
}

func groupTextSMSURI(_ phones: [String]) -> String? {
    guard !phones.isEmpty else { return nil }
    return "sms:/open?addresses=\(phones.joined(separator: ","))"
}

func groupTextSelectionLabel(_ count: Int) -> String {
    if count == 0 { return GroupTextCopy.none }
    return "\(count) \(count == 1 ? "number" : "numbers") selected"
}

func emailBlastPreview(_ count: Int) -> String {
    let noun = count == 1 ? "attendee" : "attendees"
    return "emailing \(count) \(noun) — anyone without an email is skipped"
}

func emailBlastConfirm(_ count: Int) -> String {
    let noun = count == 1 ? "attendee" : "attendees"
    return "email \(count) \(noun)? this can't be undone — anyone without an email on file will be skipped."
}

func emailBlastSuccess(sent: Int, skipped: Int) -> String {
    let noun = sent == 1 ? "attendee" : "attendees"
    let skip = skipped > 0 ? ", \(skipped) skipped (no email)" : ""
    return "sent to \(sent) \(noun)\(skip) 🌱"
}

func emailBlastErrorMessage(_ code: String?) -> String {
    switch code {
    case "perm.denied": EmailBlastCopy.forbidden
    case "event.blast_no_recipients": EmailBlastCopy.noRecipients
    case "event.blast_invalid_audience": EmailBlastCopy.invalidAudience
    default: EmailBlastCopy.failure
    }
}

private struct BlastHTTPError: Error {
    let code: String?
}

extension EventsClient {
    func textRecipients(eventId: String) async throws -> TextRecipients {
        let data = try await blastData("GET", url: textRecipientsURL(base: baseURL, eventId: eventId), body: nil)
        return try Event.decoder.decode(TextRecipients.self, from: data)
    }

    func sendEmailBlast(eventId: String, subject: String, message: String, audience: [String]) async throws -> EmailBlastResult {
        let data = try await blastData(
            "POST",
            url: emailBlastURL(base: baseURL, eventId: eventId),
            body: ["subject": subject, "message": message, "audience": audience]
        )
        return try Event.decoder.decode(EmailBlastResult.self, from: data)
    }

    private func blastData(_ method: String, url: URL, body: [String: Any]?) async throws -> Data {
        var req = URLRequest(url: url)
        req.httpMethod = method
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let body {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
            req.httpBody = try JSONSerialization.data(withJSONObject: body)
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else {
            throw BlastHTTPError(code: apiErrorCode(from: data))
        }
        return data
    }
}

struct EmailBlastResult: Decodable, Equatable {
    var sentCount: Int
    var skippedNoEmailCount: Int
    var failedCount: Int

    enum CodingKeys: String, CodingKey {
        case sentCount = "sent_count"
        case skippedNoEmailCount = "skipped_no_email_count"
        case failedCount = "failed_count"
    }
}

@Observable
final class GroupTextModel {
    var error: String?
    var busy = false
    var loaded = false
    var recipients = TextRecipients()
    var selected = ["attending", "maybe"]
    var copied = false
    var client: EventsClient
    let eventId: String

    init(client: EventsClient, eventId: String) {
        self.client = client
        self.eventId = eventId
    }

    var groups: [GroupTextOption] {
        groupTextGroups.compactMap { key, label in
            let count = recipients.phones(key).count
            guard count > 0 else { return nil }
            return GroupTextOption(value: key, label: label, count: count)
        }
    }

    var phones: [String] { groupTextPhones(recipients, selected: selected) }
    var smsURI: String? { groupTextSMSURI(phones) }
    var selectionLabel: String { groupTextSelectionLabel(phones.count) }
    var copyList: String { phones.joined(separator: ", ") }
    var textLabel: String { phones.isEmpty ? GroupTextCopy.text : "text \(phones.count)" }
    var empty: String? { loaded && groups.isEmpty ? GroupTextCopy.empty : nil }

    func load() async {
        error = nil
        busy = true
        defer { busy = false }
        do {
            recipients = try await client.textRecipients(eventId: eventId)
            loaded = true
        } catch {
            recipients = TextRecipients()
            loaded = false
            self.error = GroupTextCopy.loadError
        }
    }

    func toggle(_ key: String) {
        if let index = selected.firstIndex(of: key) {
            selected.remove(at: index)
        } else {
            selected.append(key)
        }
    }

    func copyNumbers() {
        guard !phones.isEmpty else { return }
        UIPasteboard.general.string = copyList
        copied = true
    }
}

struct EmailBlastAudience: Equatable, Identifiable {
    var status: String
    var label: String
    var count: Int
    var id: String { status }
}

@Observable
final class EmailBlastModel {
    var subject = ""
    var message = ""
    var selected: [String]
    var confirming = false
    var busy = false
    var error: String?
    var success: String?
    var client: EventsClient
    let eventId: String
    let guestStatuses: [String]

    init(client: EventsClient, eventId: String, guestStatuses: [String]) {
        self.client = client
        self.eventId = eventId
        self.guestStatuses = guestStatuses
        selected = emailBlastGroups.map(\.0).filter { status in guestStatuses.contains(status) }
    }

    var audiences: [EmailBlastAudience] {
        emailBlastGroups.compactMap { status, label in
            let count = guestStatuses.filter { $0 == status }.count
            guard count > 0 else { return nil }
            return EmailBlastAudience(status: status, label: label, count: count)
        }
    }

    var count: Int { guestStatuses.filter { selected.contains($0) }.count }
    var preview: String { emailBlastPreview(count) }
    var confirmBody: String { emailBlastConfirm(count) }

    func toggle(_ status: String) {
        if let index = selected.firstIndex(of: status) {
            selected.remove(at: index)
        } else {
            selected.append(status)
        }
    }

    func next() async {
        error = nil
        guard count > 0 else { return }
        let subject = String(subject.trimmingCharacters(in: .whitespacesAndNewlines).prefix(150))
        let message = String(message.trimmingCharacters(in: .whitespacesAndNewlines).prefix(5000))
        guard !subject.isEmpty else {
            error = EmailBlastCopy.subjectRequired
            return
        }
        guard !message.isEmpty else {
            error = EmailBlastCopy.messageRequired
            return
        }
        self.subject = subject
        self.message = message
        confirming = true
    }

    func send() async {
        guard confirming else { return }
        error = nil
        busy = true
        defer { busy = false }
        do {
            let result = try await client.sendEmailBlast(
                eventId: eventId,
                subject: subject,
                message: message,
                audience: selected
            )
            success = emailBlastSuccess(sent: result.sentCount, skipped: result.skippedNoEmailCount)
        } catch let failure as BlastHTTPError {
            error = emailBlastErrorMessage(failure.code)
        } catch {
            self.error = EmailBlastCopy.failure
        }
    }
}

struct GroupTextSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var model: GroupTextModel

    init(eventId: String, client: EventsClient) {
        _model = State(initialValue: GroupTextModel(client: client, eventId: eventId))
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                if model.busy {
                    Text(GroupTextCopy.loading)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.muted)
                } else if let error = model.error {
                    Text(error)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.muted)
                } else if let empty = model.empty {
                    Text(empty)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.muted)
                } else {
                    picker
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(PDAColor.background)
            .navigationTitle(GroupTextCopy.title)
            .navigationBarTitleDisplayMode(.inline)
        }
        .task { await model.load() }
    }

    private var picker: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(GroupTextCopy.hint)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foregroundSecondary)
            FlowChips(items: model.groups.map { ($0.value, "\($0.label) \($0.count)", model.selected.contains($0.value)) }) {
                model.toggle($0)
            }
            Text(model.selectionLabel)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
            if model.copied {
                Text("\(GroupTextCopy.copied) \(model.phones.count) numbers")
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.positive)
            }
            HStack {
                PDAButton(GroupTextCopy.copy, variant: .ghost) { model.copyNumbers() }
                    .disabled(model.phones.isEmpty)
                Spacer()
                PDAButton(GroupTextCopy.cancel, variant: .secondary) { dismiss() }
                if let uri = model.smsURI, let url = URL(string: uri) {
                    PDAButton(model.textLabel) {
                        UIApplication.shared.open(url)
                        dismiss()
                    }
                } else {
                    PDAButton(model.textLabel) {}
                        .disabled(true)
                }
            }
        }
    }
}

struct EmailBlastSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var model: EmailBlastModel

    init(eventId: String, guestStatuses: [String], client: EventsClient) {
        _model = State(initialValue: EmailBlastModel(client: client, eventId: eventId, guestStatuses: guestStatuses))
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                if let success = model.success {
                    Text(success)
                        .font(PDAType.field)
                        .foregroundStyle(PDAColor.positive)
                    HStack {
                        Spacer()
                        PDAButton(EmailBlastCopy.done) { dismiss() }
                    }
                } else if model.confirming {
                    confirm
                } else {
                    form
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(PDAColor.background)
            .navigationTitle(model.confirming ? EmailBlastCopy.confirmTitle : EmailBlastCopy.title)
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var form: some View {
        VStack(alignment: .leading, spacing: 12) {
            PDATextField(EmailBlastCopy.subject, text: $model.subject)
            PDATextField(EmailBlastCopy.message, text: $model.message, axis: .vertical, lineLimit: 6, reserveLineSpace: true)
            Text(EmailBlastCopy.sendTo)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            FlowChips(items: model.audiences.map { ($0.status, "\($0.label) \($0.count)", model.selected.contains($0.status)) }) {
                model.toggle($0)
            }
            Text(model.preview)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
            if let error = model.error {
                Text(error).font(PDAType.control).foregroundStyle(PDAColor.destructive)
            }
            HStack {
                Spacer()
                PDAButton(EmailBlastCopy.cancel, variant: .ghost) { dismiss() }
                PDAButton(EmailBlastCopy.next) { Task { await model.next() } }
                    .disabled(model.count == 0)
            }
        }
    }

    private var confirm: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(model.confirmBody)
                .font(PDAType.field)
                .foregroundStyle(PDAColor.foregroundSecondary)
            if let error = model.error {
                Text(error).font(PDAType.control).foregroundStyle(PDAColor.destructive)
            }
            HStack {
                Spacer()
                PDAButton(EmailBlastCopy.back, variant: .ghost) { model.confirming = false }
                    .disabled(model.busy)
                PDAButton(model.busy ? EmailBlastCopy.sending : EmailBlastCopy.send) {
                    Task { await model.send() }
                }
                .disabled(model.busy)
            }
        }
    }
}

private struct FlowChips: View {
    let items: [(String, String, Bool)]
    let toggle: (String) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(items, id: \.0) { item in
                    Button(item.1) { toggle(item.0) }
                        .font(PDAType.control)
                        .foregroundStyle(item.2 ? PDAColor.brand700 : PDAColor.foregroundSecondary)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 6)
                        .background(item.2 ? PDAColor.brand100 : PDAColor.surface, in: Capsule())
                        .overlay {
                            Capsule().strokeBorder(item.2 ? PDAColor.brand300 : PDAColor.border, lineWidth: 1)
                        }
                        .accessibilityAddTraits(item.2 ? .isSelected : [])
                }
            }
        }
    }
}
