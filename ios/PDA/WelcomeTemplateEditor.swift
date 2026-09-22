import SwiftUI

enum WelcomeTemplateCopy {
    static let button = "edit shared welcome template"
    static let title = "edit welcome message"
    static let field = "welcome message body"
    static let helper = "this text is shared with all vetters. changes apply everywhere."
    static let placeholders =
        "available placeholders: ${FIRST_NAME} (recipient's first name), ${SENDER_NAME}, ${MAGIC_LINK}, ${WHATSAPP_LINK}"
    static let saved = "template saved 🌱"
    static let cancel = "cancel"
    static let save = "save"
    static let saving = "saving…"
    static let loading = "loading…"
    static let required = "welcome message body is required"
    static let forbiddenTitle = "edit welcome message"
    static let forbiddenBody = "you need permission to approve join requests to edit the welcome message."
    static let loadError = "couldn't load template — try refreshing"
    static let saveError = "couldn't save template — try again"
}

enum WelcomeTemplateError: Error, Equatable {
    case forbidden
}

struct WelcomeTemplate: Decodable, Equatable {
    let body: String

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        body = try c.decodeIfPresent(String.self, forKey: .body) ?? ""
    }

    private enum CodingKeys: String, CodingKey {
        case body
    }
}

let welcomeTemplateMaxLength = 4000

func welcomeTemplateURL(base: URL) -> URL {
    URL(string: "/api/community/welcome-template/", relativeTo: base)!.absoluteURL
}

func welcomeTemplateOverLimit(_ text: String) -> Bool {
    text.count > welcomeTemplateMaxLength
}

func welcomeTemplateCounter(_ count: Int) -> String {
    "\(count) / \(welcomeTemplateMaxLength)"
}

extension EventsClient {
    func welcomeTemplate() async throws -> WelcomeTemplate {
        let (data, status) = try await welcomeTemplateRequest(method: "GET", body: nil)
        if status == 403 { throw WelcomeTemplateError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(WelcomeTemplate.self, from: data)
    }

    func saveWelcomeTemplate(_ body: String) async throws -> WelcomeTemplate {
        let payload = try JSONSerialization.data(withJSONObject: ["body": body])
        let (data, status) = try await welcomeTemplateRequest(method: "PATCH", body: payload)
        if status == 403 { throw WelcomeTemplateError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(WelcomeTemplate.self, from: data)
    }

    private func welcomeTemplateRequest(method: String, body: Data?) async throws -> (Data, Int) {
        var req = URLRequest(url: welcomeTemplateURL(base: baseURL))
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
final class WelcomeTemplateEditorModel {
    var client: EventsClient
    var body = ""
    var toast: String?
    var formError: String?
    var error: String?
    var forbidden = false
    var loaded = false
    var saving = false
    var closed = false

    var explanationTitle: String { WelcomeTemplateCopy.forbiddenTitle }
    var explanationBody: String { WelcomeTemplateCopy.forbiddenBody }
    var saveLabel: String { saving ? WelcomeTemplateCopy.saving : WelcomeTemplateCopy.save }

    var canSave: Bool {
        loaded && !saving && !forbidden && !welcomeTemplateOverLimit(body)
    }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        do {
            body = try await client.welcomeTemplate().body
            loaded = true
        } catch {
            self.error = WelcomeTemplateCopy.loadError
            loaded = true
        }
    }

    func save() async -> Bool {
        if welcomeTemplateOverLimit(body) { return false }
        if body.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            formError = WelcomeTemplateCopy.required
            return false
        }
        formError = nil
        saving = true
        defer { saving = false }
        do {
            _ = try await client.saveWelcomeTemplate(body)
            toast = WelcomeTemplateCopy.saved
            closed = true
            return true
        } catch WelcomeTemplateError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = WelcomeTemplateCopy.saveError
            return false
        }
    }

    func cancel() {
        closed = true
    }
}

struct WelcomeTemplateEditorView: View {
    var client: EventsClient
    var onSaved: () -> Void = {}
    @Environment(\.dismiss) private var dismiss
    @State private var model: WelcomeTemplateEditorModel?

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
                        Text(WelcomeTemplateCopy.helper)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                        Text(WelcomeTemplateCopy.placeholders)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        TextEditor(text: bodyBinding(model))
                            .accessibilityLabel(WelcomeTemplateCopy.field)
                            .frame(minHeight: 200)
                            .overlay(RoundedRectangle(cornerRadius: 8).stroke(.separator))
                        Text(welcomeTemplateCounter(model.body.count))
                            .font(.caption)
                            .frame(maxWidth: .infinity, alignment: .trailing)
                            .foregroundStyle(welcomeTemplateOverLimit(model.body) ? .red : .secondary)
                        if let formError = model.formError {
                            Text(formError).foregroundStyle(.red)
                        }
                    }
                    .padding()
                }
            } else {
                ProgressView(WelcomeTemplateCopy.loading)
            }
        }
        .navigationTitle(WelcomeTemplateCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                PDAButton(WelcomeTemplateCopy.cancel, variant: .secondary) {
                    model?.cancel()
                    dismiss()
                }
            }
            if model?.forbidden != true {
                ToolbarItem(placement: .confirmationAction) {
                    PDAButton(model?.saveLabel ?? WelcomeTemplateCopy.save) {
                        Task { await submit() }
                    }
                    .disabled(model?.canSave != true)
                }
            }
        }
        .task {
            if model == nil { model = WelcomeTemplateEditorModel(client: client) }
            await model?.load()
        }
    }

    private func bodyBinding(_ model: WelcomeTemplateEditorModel) -> Binding<String> {
        Binding(get: { model.body }, set: { model.body = $0 })
    }

    private func submit() async {
        guard let model, await model.save() else { return }
        onSaved()
        dismiss()
    }
}
