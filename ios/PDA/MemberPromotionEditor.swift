import SwiftUI

enum MemberPromotionCopy {
    static let button = "edit member promotion message"
    static let title = "edit member promotion message"
    static let field = "member promotion message body"
    static let helper =
        "sent when a tentatively-approved applicant is manually promoted to full member — this replaces the default message text. they already have a login, so there is no link to share."
    static let placeholders =
        "available placeholders: ${FIRST_NAME} (recipient's first name), ${SENDER_NAME}, ${WHATSAPP_LINK}"
    static let saved = "message saved 🌱"
    static let cancel = "cancel"
    static let save = "save"
    static let saving = "saving…"
    static let loading = "loading…"
    static let required = "message body is required"
    static let forbiddenTitle = "edit member promotion message"
    static let forbiddenBody = "you need permission to approve join requests to edit the member promotion message."
    static let loadError = "couldn't load the message — try refreshing"
    static let saveError = "couldn't save the message — try again"
}

enum MemberPromotionError: Error, Equatable {
    case forbidden
}

struct MemberPromotionMessage: Decodable, Equatable {
    let body: String

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        body = try c.decodeIfPresent(String.self, forKey: .body) ?? ""
    }

    private enum CodingKeys: String, CodingKey {
        case body
    }
}

let memberPromotionMaxLength = 4000

func memberPromotionMessageURL(base: URL) -> URL {
    URL(string: "/api/community/member-promotion-message/", relativeTo: base)!.absoluteURL
}

func memberPromotionOverLimit(_ text: String) -> Bool {
    text.count > memberPromotionMaxLength
}

func memberPromotionCounter(_ count: Int) -> String {
    "\(count) / \(memberPromotionMaxLength)"
}

extension EventsClient {
    func memberPromotionMessage() async throws -> MemberPromotionMessage {
        let (data, status) = try await memberPromotionRequest(method: "GET", body: nil)
        if status == 403 { throw MemberPromotionError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(MemberPromotionMessage.self, from: data)
    }

    func saveMemberPromotionMessage(_ body: String) async throws -> MemberPromotionMessage {
        let payload = try JSONSerialization.data(withJSONObject: ["body": body])
        let (data, status) = try await memberPromotionRequest(method: "PATCH", body: payload)
        if status == 403 { throw MemberPromotionError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(MemberPromotionMessage.self, from: data)
    }

    private func memberPromotionRequest(method: String, body: Data?) async throws -> (Data, Int) {
        var req = URLRequest(url: memberPromotionMessageURL(base: baseURL))
        req.httpMethod = method
        if body != nil {
            req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = body
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        return (data, status)
    }
}

@Observable
final class MemberPromotionEditorModel {
    var client: EventsClient
    var body = ""
    var toast: String?
    var formError: String?
    var error: String?
    var forbidden = false
    var loaded = false
    var saving = false
    var closed = false

    var explanationTitle: String { MemberPromotionCopy.forbiddenTitle }
    var explanationBody: String { MemberPromotionCopy.forbiddenBody }
    var saveLabel: String { saving ? MemberPromotionCopy.saving : MemberPromotionCopy.save }

    var canSave: Bool {
        loaded && !saving && !forbidden && !memberPromotionOverLimit(body)
    }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        do {
            body = try await client.memberPromotionMessage().body
            loaded = true
        } catch {
            self.error = MemberPromotionCopy.loadError
            loaded = true
        }
    }

    func save() async -> Bool {
        if memberPromotionOverLimit(body) { return false }
        if body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            formError = MemberPromotionCopy.required
            return false
        }
        formError = nil
        saving = true
        defer { saving = false }
        do {
            _ = try await client.saveMemberPromotionMessage(body)
            toast = MemberPromotionCopy.saved
            closed = true
            return true
        } catch MemberPromotionError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = MemberPromotionCopy.saveError
            return false
        }
    }

    func cancel() {
        closed = true
    }
}

struct MemberPromotionEditorView: View {
    var client: EventsClient
    var onSaved: () -> Void = {}
    @Environment(\.dismiss) private var dismiss
    @State private var model: MemberPromotionEditorModel?

    var body: some View {
        Group {
            if let model, model.forbidden {
                VStack(alignment: .leading, spacing: 12) {
                    Text(model.explanationTitle).font(.title2)
                    Text(model.explanationBody).foregroundStyle(.secondary)
                    Spacer()
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
            } else if let model, let error = model.error {
                ContentUnavailableView(error, systemImage: "exclamationmark.triangle")
            } else if let model, model.loaded {
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(MemberPromotionCopy.helper)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                        Text(MemberPromotionCopy.placeholders)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        TextEditor(text: bodyBinding(model))
                            .accessibilityLabel(MemberPromotionCopy.field)
                            .frame(minHeight: 200)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(.separator))
                        Text(memberPromotionCounter(model.body.count))
                            .font(.caption)
                            .frame(maxWidth: .infinity, alignment: .trailing)
                            .foregroundStyle(memberPromotionOverLimit(model.body) ? .red : .secondary)
                        if let formError = model.formError {
                            Text(formError).foregroundStyle(.red)
                        }
                    }
                    .padding()
                }
            } else {
                ProgressView(MemberPromotionCopy.loading)
            }
        }
        .navigationTitle(MemberPromotionCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(MemberPromotionCopy.cancel) {
                    model?.cancel()
                    dismiss()
                }
            }
            if model?.forbidden != true {
                ToolbarItem(placement: .confirmationAction) {
                    Button(model?.saveLabel ?? MemberPromotionCopy.save) {
                        Task { await submit() }
                    }
                    .disabled(model?.canSave != true)
                }
            }
        }
        .task {
            if model == nil { model = MemberPromotionEditorModel(client: client) }
            await model?.load()
        }
    }

    private func bodyBinding(_ model: MemberPromotionEditorModel) -> Binding<String> {
        Binding(get: { model.body }, set: { model.body = $0 })
    }

    private func submit() async {
        guard let model, await model.save() else { return }
        onSaved()
        dismiss()
    }
}
