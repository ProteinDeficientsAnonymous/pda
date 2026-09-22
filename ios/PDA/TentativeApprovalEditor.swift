import SwiftUI

enum TentativeApprovalCopy {
    static let button = "edit tentative approval message"
    static let title = "edit tentative approval message"
    static let field = "tentative approval message body"
    static let helper = "sent when someone is tentatively approved — this replaces the default message text."
    static let placeholders =
        "available placeholders: ${FIRST_NAME} (recipient's first name), ${SENDER_NAME}, ${MAGIC_LINK} (their one-time sign in link), ${WHATSAPP_LINK}"
    static let saved = "message saved 🌱"
    static let cancel = "cancel"
    static let save = "save"
    static let saving = "saving…"
    static let loading = "loading…"
    static let required = "message body is required"
    static let forbiddenTitle = "edit tentative approval message"
    static let forbiddenBody = "you need permission to approve join requests to edit the tentative approval message."
    static let loadError = "couldn't load the message — try refreshing"
    static let saveError = "couldn't save the message — try again"
}

enum TentativeApprovalError: Error, Equatable {
    case forbidden
}

struct TentativeApprovalMessage: Decodable, Equatable {
    let body: String

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        body = try c.decodeIfPresent(String.self, forKey: .body) ?? ""
    }

    private enum CodingKeys: String, CodingKey {
        case body
    }
}

let tentativeApprovalMaxLength = 4000

func tentativeApprovalMessageURL(base: URL) -> URL {
    URL(string: "/api/community/tentative-approval-message/", relativeTo: base)!.absoluteURL
}

func tentativeApprovalOverLimit(_ text: String) -> Bool {
    text.count > tentativeApprovalMaxLength
}

func tentativeApprovalCounter(_ count: Int) -> String {
    "\(count) / \(tentativeApprovalMaxLength)"
}

extension EventsClient {
    func tentativeApprovalMessage() async throws -> TentativeApprovalMessage {
        let (data, status) = try await tentativeApprovalRequest(method: "GET", body: nil)
        if status == 403 { throw TentativeApprovalError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(TentativeApprovalMessage.self, from: data)
    }

    func saveTentativeApprovalMessage(_ body: String) async throws -> TentativeApprovalMessage {
        let payload = try JSONSerialization.data(withJSONObject: ["body": body])
        let (data, status) = try await tentativeApprovalRequest(method: "PATCH", body: payload)
        if status == 403 { throw TentativeApprovalError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(TentativeApprovalMessage.self, from: data)
    }

    private func tentativeApprovalRequest(method: String, body: Data?) async throws -> (Data, Int) {
        var req = URLRequest(url: tentativeApprovalMessageURL(base: baseURL))
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
final class TentativeApprovalEditorModel {
    var client: EventsClient
    var body = ""
    var toast: String?
    var formError: String?
    var error: String?
    var forbidden = false
    var loaded = false
    var saving = false
    var closed = false

    var explanationTitle: String { TentativeApprovalCopy.forbiddenTitle }
    var explanationBody: String { TentativeApprovalCopy.forbiddenBody }
    var saveLabel: String { saving ? TentativeApprovalCopy.saving : TentativeApprovalCopy.save }

    var canSave: Bool {
        loaded && !saving && !forbidden && !tentativeApprovalOverLimit(body)
    }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        do {
            body = try await client.tentativeApprovalMessage().body
            loaded = true
        } catch {
            self.error = TentativeApprovalCopy.loadError
            loaded = true
        }
    }

    func save() async -> Bool {
        if tentativeApprovalOverLimit(body) { return false }
        if body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            formError = TentativeApprovalCopy.required
            return false
        }
        formError = nil
        saving = true
        defer { saving = false }
        do {
            _ = try await client.saveTentativeApprovalMessage(body)
            toast = TentativeApprovalCopy.saved
            closed = true
            return true
        } catch TentativeApprovalError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = TentativeApprovalCopy.saveError
            return false
        }
    }

    func cancel() {
        closed = true
    }
}

struct TentativeApprovalEditorView: View {
    var client: EventsClient
    var onSaved: () -> Void = {}
    @Environment(\.dismiss) private var dismiss
    @State private var model: TentativeApprovalEditorModel?

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
                        Text(TentativeApprovalCopy.helper)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                        Text(TentativeApprovalCopy.placeholders)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        TextEditor(text: bodyBinding(model))
                            .accessibilityLabel(TentativeApprovalCopy.field)
                            .frame(minHeight: 200)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(.separator))
                        Text(tentativeApprovalCounter(model.body.count))
                            .font(.caption)
                            .frame(maxWidth: .infinity, alignment: .trailing)
                            .foregroundStyle(tentativeApprovalOverLimit(model.body) ? .red : .secondary)
                        if let formError = model.formError {
                            Text(formError).foregroundStyle(.red)
                        }
                    }
                    .padding()
                }
            } else {
                ProgressView(TentativeApprovalCopy.loading)
            }
        }
        .navigationTitle(TentativeApprovalCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(TentativeApprovalCopy.cancel) {
                    model?.cancel()
                    dismiss()
                }
            }
            if model?.forbidden != true {
                ToolbarItem(placement: .confirmationAction) {
                    Button(model?.saveLabel ?? TentativeApprovalCopy.save) {
                        Task { await submit() }
                    }
                    .disabled(model?.canSave != true)
                }
            }
        }
        .task {
            if model == nil { model = TentativeApprovalEditorModel(client: client) }
            await model?.load()
        }
    }

    private func bodyBinding(_ model: TentativeApprovalEditorModel) -> Binding<String> {
        Binding(get: { model.body }, set: { model.body = $0 })
    }

    private func submit() async {
        guard let model, await model.save() else { return }
        onSaved()
        dismiss()
    }
}
