import SwiftUI

enum BulkCreateCopy {
    static let button = "bulk add"
    static let title = "bulk add members"
    static let phoneNumbers = "phone numbers"
    static let hint = "one per line — us numbers assumed unless prefixed with + and a country code"
    static let placeholder = "555-123-4567\n+44 20 7946 0958"
    static let cancel = "cancel"
    static let create = "create members"
    static let creating = "creating…"
    static let empty = "add at least one phone number"
    static let failure = "couldn't create members — try again"
    static let forbidden = "you don't have permission to do that"
    static let resultsTitle = "bulk results"
    static let created = "created"
    static let failed = "failed"
    static let copyLink = "copy link"
    static let copied = "copied ✓"
    static let sendWelcome = "send welcome message"
    static let done = "done"
    static let unknownError = "unknown error"
}

struct BulkCreateResult: Decodable, Equatable, Identifiable {
    let row: Int
    let phoneNumber: String
    let success: Bool
    let error: String?
    let magicLinkToken: String?

    var id: Int { row }

    enum CodingKeys: String, CodingKey {
        case row
        case phoneNumber = "phone_number"
        case success
        case error
        case magicLinkToken = "magic_link_token"
    }
}

struct BulkCreateResponse: Decodable, Equatable {
    let results: [BulkCreateResult]
    let created: Int
    let failed: Int
}

enum BulkCreateError: Error {
    case failed(String)
}

func bulkCreateURL(base: URL) -> URL {
    URL(string: "/api/auth/bulk-create-users/", relativeTo: base)!.absoluteURL
}

func bulkMemberPhones(_ raw: String) -> [String] {
    raw.split(separator: "\n", omittingEmptySubsequences: false)
        .map { String($0).trimmingCharacters(in: .whitespacesAndNewlines) }
        .filter { !$0.isEmpty }
        .map(normalizeBulkPhone)
}

func normalizeBulkPhone(_ input: String) -> String {
    let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.hasPrefix("+") { return trimmed }
    let digits = trimmed.filter(\.isNumber)
    if digits.isEmpty { return trimmed }
    if digits.count == 10 { return "+1\(digits)" }
    if digits.count == 11, digits.hasPrefix("1") { return "+\(digits)" }
    return "+\(digits)"
}

func bulkResultsSummary(created: Int, failed: Int) -> String {
    "created \(created) of \(created + failed) — share each magic link with its recipient; links won't be shown again."
}

func bulkResultLink(base: URL, token: String?) -> String {
    guard let token, !token.isEmpty else { return "" }
    return magicLoginURL(base: base, token: token)
}

func bulkResultSMS(phone: String, url: String) -> String {
    guard !url.isEmpty else { return "" }
    return memberSmsLink(phone: phone, message: memberWelcomeMessage(firstName: "", url: url))
}

func bulkFailureLine(phone: String, error: String?) -> String {
    "\(formatMemberPhone(phone)) — \(error ?? BulkCreateCopy.unknownError)"
}

func bulkCreateDenied(_ data: Data) -> Bool {
    guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
          let detail = json["detail"] as? [[String: Any]] else { return false }
    return detail.contains { ($0["code"] as? String) == "perm.denied" }
}

extension EventsClient {
    func bulkCreateMembers(phoneNumbers: [String]) async throws -> BulkCreateResponse {
        var req = URLRequest(url: bulkCreateURL(base: baseURL))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: ["phone_numbers": phoneNumbers])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if !(200 ..< 300).contains(status) {
            let message = bulkCreateDenied(data) ? BulkCreateCopy.forbidden : BulkCreateCopy.failure
            throw BulkCreateError.failed(message)
        }
        return try Event.decoder.decode(BulkCreateResponse.self, from: data)
    }
}

@Observable
final class BulkCreateModel {
    var client: EventsClient
    var raw = ""
    var formError: String?
    var response: BulkCreateResponse?
    var saving = false
    var copiedRow: Int?

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func submit() async {
        formError = nil
        let numbers = bulkMemberPhones(raw)
        if numbers.isEmpty {
            formError = BulkCreateCopy.empty
            return
        }
        saving = true
        defer { saving = false }
        do {
            response = try await client.bulkCreateMembers(phoneNumbers: numbers)
        } catch let BulkCreateError.failed(message) {
            formError = message
        } catch {
            formError = BulkCreateCopy.failure
        }
    }

    func copy(row: Int) {
        copiedRow = row
    }

    func copyLabel(row: Int) -> String {
        copiedRow == row ? BulkCreateCopy.copied : BulkCreateCopy.copyLink
    }
}

struct BulkCreateView: View {
    var client: EventsClient
    @Environment(\.dismiss) private var dismiss
    @State private var model: BulkCreateModel?

    var body: some View {
        Group {
            if let model, let response = model.response {
                results(model, response)
            } else if let model {
                form(model)
            }
        }
        .navigationTitle(model?.response == nil ? BulkCreateCopy.title : BulkCreateCopy.resultsTitle)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = BulkCreateModel(client: client) }
        }
    }

    private func form(_ model: BulkCreateModel) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 12) {
                PDATextField(
                    BulkCreateCopy.phoneNumbers,
                    text: Bindable(model).raw,
                    axis: .vertical,
                    capitalization: .never,
                    disableAutocorrection: true,
                    lineLimit: 8
                )
                Text(BulkCreateCopy.hint)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.muted)
                Text(BulkCreateCopy.placeholder)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.mutedForeground)
                if let formError = model.formError {
                    Text(formError)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.destructive)
                }
                HStack {
                    Spacer()
                    PDAButton(BulkCreateCopy.cancel, variant: .ghost) { dismiss() }
                    PDAButton(model.saving ? BulkCreateCopy.creating : BulkCreateCopy.create) {
                        Task { await model.submit() }
                    }
                    .disabled(model.saving)
                }
            }
            .padding()
        }
    }

    private func results(_ model: BulkCreateModel, _ response: BulkCreateResponse) -> some View {
        let created = response.results.filter(\.success)
        let failed = response.results.filter { !$0.success }
        return ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(bulkResultsSummary(created: response.created, failed: response.failed))
                    .font(PDAType.field)
                    .foregroundStyle(PDAColor.foregroundSecondary)
                if !created.isEmpty {
                    Text(BulkCreateCopy.created)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.muted)
                    ForEach(created) { result in
                        createdRow(model, result)
                    }
                }
                if !failed.isEmpty {
                    Text(BulkCreateCopy.failed)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.muted)
                    ForEach(failed) { result in
                        Text(bulkFailureLine(phone: result.phoneNumber, error: result.error))
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.destructive)
                    }
                }
                HStack {
                    Spacer()
                    PDAButton(BulkCreateCopy.done) { dismiss() }
                }
            }
            .padding()
        }
    }

    private func createdRow(_ model: BulkCreateModel, _ result: BulkCreateResult) -> some View {
        let link = bulkResultLink(base: model.client.baseURL, token: result.magicLinkToken)
        let sms = bulkResultSMS(phone: result.phoneNumber, url: link)
        return VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(formatMemberPhone(result.phoneNumber).lowercased())
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foreground)
                Spacer()
                PDAButton(model.copyLabel(row: result.row), variant: .secondary) {
                    UIPasteboard.general.string = link
                    model.copy(row: result.row)
                }
                if let url = URL(string: sms), !sms.isEmpty {
                    Link(BulkCreateCopy.sendWelcome, destination: url)
                        .font(PDAType.control)
                }
            }
            if !link.isEmpty {
                Text(link)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foreground)
                    .textSelection(.enabled)
            }
        }
        .padding(12)
        .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.md))
        .overlay {
            RoundedRectangle(cornerRadius: PDARadius.md)
                .strokeBorder(PDAColor.border, lineWidth: 1)
        }
    }
}
