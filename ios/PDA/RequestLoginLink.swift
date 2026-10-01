import SwiftUI

enum RequestLoginLinkCopy {
    static let button = "request a login link"
    static let title = "request a login link"
    static let hint = "enter your phone number and we'll send a one-tap login link to the email on file"
    static let phone = "phone number"
    static let cancel = "cancel"
    static let submit = "request link"
    static let submitting = "requesting…"
    static let done = "done"
    static let invalidPhone = "enter a valid phone number"
    static let email =
        "if there's an account for that number, we sent a login link to the email on file — check your inbox, including spam 🌱"
    static let admin =
        "if there's an account for that number, an admin will follow up with your login link — sit tight 🌱"
    static let cooldown =
        "we didn't send a new link — you requested one just a moment ago, and it's still valid. check your inbox, including spam."
    static let readyNow = "you can request another link now"
    static let failure = "couldn't send the request — try again"
}

struct RequestLoginLinkResult: Decodable, Equatable {
    var detail: String
    var delivery: String
    var retryAfterSeconds: Int?

    enum CodingKeys: String, CodingKey {
        case detail
        case delivery
        case retryAfterSeconds = "retry_after_seconds"
    }
}

struct RequestLoginLinkFailure: Error {
    var message: String
}

func requestLoginLinkURL(base: URL) -> URL {
    URL(string: "/api/community/request-login-link/", relativeTo: base)!.absoluteURL
}

func requestLoginLinkCountdown(_ totalSeconds: Int) -> String {
    let minutes = totalSeconds / 60
    let seconds = totalSeconds % 60
    return "\(minutes):" + String(format: "%02d", seconds)
}

func requestLoginLinkFollowup(seconds: Int) -> String {
    if seconds > 0 {
        return "try again in \(requestLoginLinkCountdown(seconds))"
    }
    return RequestLoginLinkCopy.readyNow
}

// ponytail: E.164 shape, not libphonenumber metadata. Upgrade path is PhoneNumberKit.
func isRequestLoginPhone(_ raw: String) -> Bool {
    let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
    guard trimmed.hasPrefix("+") else { return false }
    let digits = trimmed.dropFirst()
    guard digits.allSatisfy(\.isNumber) else { return false }
    return (8 ... 15).contains(digits.count)
}

func requestLoginLinkFailureMessage(_ data: Data) -> String {
    struct Box: Decodable { let detail: String? }
    if let detail = try? JSONDecoder().decode(Box.self, from: data).detail, !detail.isEmpty {
        return detail
    }
    return RequestLoginLinkCopy.failure
}

extension SessionClient {
    func requestLoginLink(phone: String) async throws -> RequestLoginLinkResult {
        var req = URLRequest(url: requestLoginLinkURL(base: baseURL))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: ["phone_number": phone])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else {
            throw RequestLoginLinkFailure(message: requestLoginLinkFailureMessage(data))
        }
        return try Event.decoder.decode(RequestLoginLinkResult.self, from: data)
    }
}

@Observable
final class RequestLoginLinkModel {
    var phone: String
    var error: String?
    var busy = false
    var delivery: String?
    var retryAfterSeconds: Int?
    var client: SessionClient

    init(client: SessionClient, phone: String) {
        self.client = client
        self.phone = phone
    }

    var successMessage: String? {
        switch delivery {
        case "email": RequestLoginLinkCopy.email
        case "admin": RequestLoginLinkCopy.admin
        default: nil
        }
    }

    var cooldownBody: String? {
        delivery == "cooldown" ? RequestLoginLinkCopy.cooldown : nil
    }

    var cooldownFollowup: String? {
        guard delivery == "cooldown" else { return nil }
        return requestLoginLinkFollowup(seconds: retryAfterSeconds ?? 0)
    }

    func submit() async {
        error = nil
        guard isRequestLoginPhone(phone) else {
            error = RequestLoginLinkCopy.invalidPhone
            return
        }
        busy = true
        defer { busy = false }
        do {
            let result = try await client.requestLoginLink(phone: phone)
            delivery = result.delivery
            retryAfterSeconds = result.retryAfterSeconds
        } catch let failure as RequestLoginLinkFailure {
            delivery = nil
            error = failure.message
        } catch {
            delivery = nil
            self.error = RequestLoginLinkCopy.failure
        }
    }
}

struct RequestLoginLinkSheet: View {
    @Environment(\.dismiss) private var dismiss
    @State private var model: RequestLoginLinkModel

    init(client: SessionClient, phone: String) {
        _model = State(initialValue: RequestLoginLinkModel(client: client, phone: phone))
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                if model.delivery == "cooldown" {
                    RequestLoginLinkCooldownNote(seconds: model.retryAfterSeconds ?? 0)
                    doneRow
                } else if let message = model.successMessage {
                    Text(message)
                        .font(PDAType.field)
                        .foregroundStyle(PDAColor.muted)
                    doneRow
                } else {
                    form
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(PDAColor.background)
            .navigationTitle(RequestLoginLinkCopy.title)
            .navigationBarTitleDisplayMode(.inline)
        }
    }

    private var form: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(RequestLoginLinkCopy.hint)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
            PDATextField(
                RequestLoginLinkCopy.phone,
                text: $model.phone,
                capitalization: .never,
                disableAutocorrection: true,
                keyboard: .phonePad,
                contentType: .telephoneNumber,
                identifier: "request-login-phone"
            )
            if let error = model.error {
                Text(error)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.destructive)
            }
            HStack {
                Spacer()
                PDAButton(RequestLoginLinkCopy.cancel, variant: .ghost) { dismiss() }
                    .disabled(model.busy)
                PDAButton(model.busy ? RequestLoginLinkCopy.submitting : RequestLoginLinkCopy.submit) {
                    Task { await model.submit() }
                }
                .disabled(model.busy)
            }
        }
    }

    private var doneRow: some View {
        HStack {
            Spacer()
            PDAButton(RequestLoginLinkCopy.done) { dismiss() }
        }
    }
}

private struct RequestLoginLinkCooldownNote: View {
    let initialSeconds: Int
    @State private var remaining: Int

    init(seconds: Int) {
        let start = max(0, seconds)
        initialSeconds = start
        _remaining = State(initialValue: start)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(RequestLoginLinkCopy.cooldown)
            Text(requestLoginLinkFollowup(seconds: remaining))
                .fontWeight(.medium)
        }
        .font(PDAType.control)
        .foregroundStyle(PDAColor.warning)
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(PDAColor.warningSubtle, in: RoundedRectangle(cornerRadius: PDARadius.md))
        .overlay {
            RoundedRectangle(cornerRadius: PDARadius.md)
                .strokeBorder(PDAColor.warning, lineWidth: 1)
        }
        .task(id: initialSeconds) {
            while remaining > 0 {
                try? await Task.sleep(for: .seconds(1))
                if Task.isCancelled { return }
                remaining = max(0, remaining - 1)
            }
        }
    }
}
