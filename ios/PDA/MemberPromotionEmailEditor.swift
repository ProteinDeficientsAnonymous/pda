import SwiftUI

enum MemberPromotionEmailCopy {
    static let button = "edit member promotion email"
    static let title = "edit member promotion email"
    static let field = "member promotion email body"
    static let helper =
        "sent automatically when a tentatively-approved applicant becomes a full member — on event check-in or manual promotion. links in the body are turned into clickable links."
    static let placeholders =
        "available placeholders: ${FIRST_NAME} (recipient's first name), ${WHATSAPP_LINK}"
    static let saved = "email saved 🌱"
    static let cancel = "cancel"
    static let save = "save"
    static let saving = "saving…"
    static let loading = "loading…"
    static let required = "message body is required"
    static let forbiddenTitle = "edit member promotion email"
    static let forbiddenBody = "you need permission to approve join requests to edit the member promotion email."
    static let loadError = "couldn't load the email — try refreshing"
    static let saveError = "couldn't save the email — try again"
}

enum MemberPromotionEmailError: Error, Equatable {
    case forbidden
}

struct MemberPromotionEmail: Decodable, Equatable {
    let body: String

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        body = try c.decodeIfPresent(String.self, forKey: .body) ?? ""
    }

    private enum CodingKeys: String, CodingKey {
        case body
    }
}

let memberPromotionEmailMaxLength = 4000

func memberPromotionEmailURL(base: URL) -> URL {
    URL(string: "/api/community/member-promotion-email/", relativeTo: base)!.absoluteURL
}

func memberPromotionEmailOverLimit(_ text: String) -> Bool {
    text.count > memberPromotionEmailMaxLength
}

func memberPromotionEmailCounter(_ count: Int) -> String {
    "\(count) / \(memberPromotionEmailMaxLength)"
}

extension EventsClient {
    func memberPromotionEmail() async throws -> MemberPromotionEmail {
        let (data, status) = try await memberPromotionEmailRequest(method: "GET", body: nil)
        if status == 403 { throw MemberPromotionEmailError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(MemberPromotionEmail.self, from: data)
    }

    func saveMemberPromotionEmail(_ body: String) async throws -> MemberPromotionEmail {
        let payload = try JSONSerialization.data(withJSONObject: ["body": body])
        let (data, status) = try await memberPromotionEmailRequest(method: "PATCH", body: payload)
        if status == 403 { throw MemberPromotionEmailError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(MemberPromotionEmail.self, from: data)
    }

    private func memberPromotionEmailRequest(method: String, body: Data?) async throws -> (Data, Int) {
        var req = URLRequest(url: memberPromotionEmailURL(base: baseURL))
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
final class MemberPromotionEmailEditorModel {
    var client: EventsClient
    var body = ""
    var toast: String?
    var formError: String?
    var error: String?
    var forbidden = false
    var loaded = false
    var saving = false
    var closed = false

    var explanationTitle: String { MemberPromotionEmailCopy.forbiddenTitle }
    var explanationBody: String { MemberPromotionEmailCopy.forbiddenBody }
    var saveLabel: String { saving ? MemberPromotionEmailCopy.saving : MemberPromotionEmailCopy.save }

    var canSave: Bool {
        loaded && !saving && !forbidden && !memberPromotionEmailOverLimit(body)
    }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        do {
            body = try await client.memberPromotionEmail().body
            loaded = true
        } catch {
            self.error = MemberPromotionEmailCopy.loadError
            loaded = true
        }
    }

    func save() async -> Bool {
        if memberPromotionEmailOverLimit(body) { return false }
        if body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            formError = MemberPromotionEmailCopy.required
            return false
        }
        formError = nil
        saving = true
        defer { saving = false }
        do {
            _ = try await client.saveMemberPromotionEmail(body)
            toast = MemberPromotionEmailCopy.saved
            closed = true
            return true
        } catch MemberPromotionEmailError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = MemberPromotionEmailCopy.saveError
            return false
        }
    }

    func cancel() {
        closed = true
    }
}

struct MemberPromotionEmailEditorView: View {
    var client: EventsClient
    var onSaved: () -> Void = {}
    @Environment(\.dismiss) private var dismiss
    @State private var model: MemberPromotionEmailEditorModel?

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
                        Text(MemberPromotionEmailCopy.helper)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                        Text(MemberPromotionEmailCopy.placeholders)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        TextEditor(text: bodyBinding(model))
                            .accessibilityLabel(MemberPromotionEmailCopy.field)
                            .frame(minHeight: 200)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(.separator))
                        Text(memberPromotionEmailCounter(model.body.count))
                            .font(.caption)
                            .frame(maxWidth: .infinity, alignment: .trailing)
                            .foregroundStyle(memberPromotionEmailOverLimit(model.body) ? .red : .secondary)
                        if let formError = model.formError {
                            Text(formError).foregroundStyle(.red)
                        }
                    }
                    .padding()
                }
            } else {
                ProgressView(MemberPromotionEmailCopy.loading)
            }
        }
        .navigationTitle(MemberPromotionEmailCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                PDAButton(MemberPromotionEmailCopy.cancel, variant: .secondary) {
                    model?.cancel()
                    dismiss()
                }
            }
            if model?.forbidden != true {
                ToolbarItem(placement: .confirmationAction) {
                    PDAButton(model?.saveLabel ?? MemberPromotionEmailCopy.save) {
                        Task { await submit() }
                    }
                    .disabled(model?.canSave != true)
                }
            }
        }
        .task {
            if model == nil { model = MemberPromotionEmailEditorModel(client: client) }
            await model?.load()
        }
    }

    private func bodyBinding(_ model: MemberPromotionEmailEditorModel) -> Binding<String> {
        Binding(get: { model.body }, set: { model.body = $0 })
    }

    private func submit() async {
        guard let model, await model.save() else { return }
        onSaved()
        dismiss()
    }
}
