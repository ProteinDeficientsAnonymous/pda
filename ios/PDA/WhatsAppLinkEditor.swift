import SwiftUI

enum WhatsAppLinkCopy {
    static let button = "edit whatsapp link"
    static let title = "edit whatsapp link"
    static let placeholder = "https://chat.whatsapp.com/…"
    static let saved = "whatsapp link saved"
    static let cancel = "cancel"
    static let save = "save"
    static let saving = "saving…"
    static let loading = "loading…"
    static let forbiddenTitle = "edit whatsapp link"
    static let forbiddenBody = "you need permission to approve join requests to edit this link."
    static let hostError = "whatsapp link must be from chat.whatsapp.com, wa.me, or whats.app"
    static let pathError = "link must point to a specific page, not just a homepage"
    static let invalid = "enter a valid url"
    static let loadError = "couldn't load the link — try refreshing"
    static let saveError = "couldn't save the link — try again"
}

enum WhatsAppLinkError: Error, Equatable {
    case forbidden
}

struct WhatsAppLink: Decodable, Equatable {
    let link: String
    let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case link
        case updatedAt = "updated_at"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        link = try c.decodeIfPresent(String.self, forKey: .link) ?? ""
        updatedAt = try c.decodeIfPresent(String.self, forKey: .updatedAt) ?? ""
    }
}

let whatsAppLinkMaxLength = 200

private let whatsAppLinkHosts: Set<String> = ["chat.whatsapp.com", "wa.me", "whats.app"]

func whatsAppLinkURL(base: URL) -> URL {
    URL(string: "/api/community/whatsapp-link/", relativeTo: base)!.absoluteURL
}

func whatsAppLinkOverLimit(_ text: String) -> Bool {
    text.count > whatsAppLinkMaxLength
}

func whatsAppLinkHostError(_ text: String) -> String? {
    let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.isEmpty { return nil }
    let normalized = trimmed.hasPrefix("http://") || trimmed.hasPrefix("https://")
        ? trimmed
        : "https://\(trimmed)"
    guard let parts = URL(string: normalized), let host = parts.host?.lowercased() else {
        return WhatsAppLinkCopy.invalid
    }
    let bare = host.hasPrefix("www.") ? String(host.dropFirst(4)) : host
    if !whatsAppLinkHosts.contains(bare) { return WhatsAppLinkCopy.hostError }
    if parts.path.trimmingCharacters(in: CharacterSet(charactersIn: "/")).isEmpty {
        return WhatsAppLinkCopy.pathError
    }
    return nil
}

extension EventsClient {
    func whatsAppLink() async throws -> WhatsAppLink {
        let (data, status) = try await whatsAppLinkRequest(method: "GET", body: nil)
        if status == 403 { throw WhatsAppLinkError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(WhatsAppLink.self, from: data)
    }

    func saveWhatsAppLink(_ link: String) async throws -> WhatsAppLink {
        let trimmed = link.trimmingCharacters(in: .whitespacesAndNewlines)
        let body = try JSONSerialization.data(withJSONObject: ["link": trimmed])
        let (data, status) = try await whatsAppLinkRequest(method: "PATCH", body: body)
        if status == 403 { throw WhatsAppLinkError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(WhatsAppLink.self, from: data)
    }

    private func whatsAppLinkRequest(method: String, body: Data?) async throws -> (Data, Int) {
        var req = URLRequest(url: whatsAppLinkURL(base: baseURL))
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
final class WhatsAppLinkEditorModel {
    var client: EventsClient
    var link = ""
    var toast: String?
    var formError: String?
    var error: String?
    var forbidden = false
    var loaded = false
    var saving = false
    var closed = false

    var explanationTitle: String { WhatsAppLinkCopy.forbiddenTitle }
    var explanationBody: String { WhatsAppLinkCopy.forbiddenBody }

    var canSave: Bool {
        loaded && !saving && !forbidden && error == nil
            && !whatsAppLinkOverLimit(link) && whatsAppLinkHostError(link) == nil
    }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        do {
            link = try await client.whatsAppLink().link
            loaded = true
        } catch {
            self.error = WhatsAppLinkCopy.loadError
            loaded = true
        }
    }

    func save() async -> Bool {
        if whatsAppLinkOverLimit(link) { return false }
        if let issue = whatsAppLinkHostError(link) {
            formError = issue
            return false
        }
        formError = nil
        saving = true
        defer { saving = false }
        do {
            _ = try await client.saveWhatsAppLink(link)
            toast = WhatsAppLinkCopy.saved
            closed = true
            return true
        } catch WhatsAppLinkError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = WhatsAppLinkCopy.saveError
            return false
        }
    }

    func cancel() {
        closed = true
    }
}

struct WhatsAppLinkEditorView: View {
    var client: EventsClient
    var onSaved: () -> Void = {}
    @Environment(\.dismiss) private var dismiss
    @State private var model: WhatsAppLinkEditorModel?

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
                Form {
                    TextField(WhatsAppLinkCopy.placeholder, text: linkBinding(model))
                        .textInputAutocapitalization(.never)
                        .keyboardType(.URL)
                        .autocorrectionDisabled()
                    if let formError = model.formError {
                        Text(formError).foregroundStyle(.red)
                    }
                }
            } else {
                ProgressView(WhatsAppLinkCopy.loading)
            }
        }
        .navigationTitle(WhatsAppLinkCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(WhatsAppLinkCopy.cancel) {
                    model?.cancel()
                    dismiss()
                }
            }
            if model?.forbidden != true {
                ToolbarItem(placement: .confirmationAction) {
                    Button(model?.saving == true ? WhatsAppLinkCopy.saving : WhatsAppLinkCopy.save) {
                        Task { await submit() }
                    }
                    .disabled(model?.canSave != true)
                }
            }
        }
        .task {
            if model == nil { model = WhatsAppLinkEditorModel(client: client) }
            await model?.load()
        }
    }

    private func linkBinding(_ model: WhatsAppLinkEditorModel) -> Binding<String> {
        Binding(get: { model.link }, set: { model.link = $0 })
    }

    private func submit() async {
        guard let model, await model.save() else { return }
        onSaved()
        dismiss()
    }
}
