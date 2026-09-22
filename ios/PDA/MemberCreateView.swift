import SwiftUI

enum MemberCreateCopy {
    static let button = "add member"
    static let title = "add member"
    static let firstName = "first name"
    static let lastName = "last name (optional)"
    static let phone = "phone number"
    static let email = "email"
    static let cancel = "cancel"
    static let create = "create"
    static let creating = "creating…"
    static let welcomeBody = "share this one-time login link; it won't be shown again."
    static let copyLink = "copy link"
    static let copied = "copied ✓"
    static let sendWelcome = "send welcome message"
    static let done = "done"
    static let firstNameRequired = "first name is required"
    static let phoneRequired = "phone number is required"
    static let emailRequired = "email is required"
    static let failure = "couldn't create member — try again"
    static let forbiddenTitle = "add member"
    static let forbiddenBody = "you need permission to create users to add a member."
}

enum MemberCreateError: Error, Equatable {
    case forbidden
}

struct CreatedMember: Decodable, Equatable {
    let id: String
    let phoneNumber: String
    let fullName: String
    let firstName: String
    let magicLinkToken: String

    enum CodingKeys: String, CodingKey {
        case id
        case phoneNumber = "phone_number"
        case fullName = "full_name"
        case firstName = "first_name"
        case magicLinkToken = "magic_link_token"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        phoneNumber = try c.decodeIfPresent(String.self, forKey: .phoneNumber) ?? ""
        fullName = try c.decodeIfPresent(String.self, forKey: .fullName) ?? ""
        firstName = try c.decodeIfPresent(String.self, forKey: .firstName) ?? ""
        magicLinkToken = try c.decodeIfPresent(String.self, forKey: .magicLinkToken) ?? ""
    }
}

func createMemberURL(base: URL) -> URL {
    URL(string: "/api/auth/create-user/", relativeTo: base)!.absoluteURL
}

func showsAddMemberButton(tab: String) -> Bool {
    tab == "members"
}

func formatMemberPhone(_ raw: String) -> String {
    let digits = raw.filter(\.isNumber)
    let national: Substring
    if digits.count == 11, digits.first == "1" {
        national = digits.dropFirst()
    } else if digits.count == 10 {
        national = Substring(digits)
    } else {
        return raw
    }
    let area = national.prefix(3)
    let middle = national.dropFirst(3).prefix(3)
    let last = national.suffix(4)
    return "(\(area)) \(middle)-\(last)"
}

func memberWelcomeTitle(fullName: String, phone: String) -> String {
    let name = fullName.trimmingCharacters(in: .whitespacesAndNewlines)
    let who = name.isEmpty ? formatMemberPhone(phone) : name.lowercased()
    return "welcome \(who)"
}

func magicLoginURL(base: URL, token: String) -> String {
    URL(string: "/magic-login/\(token)", relativeTo: base)!.absoluteURL.absoluteString
}

func memberWelcomeMessage(firstName: String, url: String) -> String {
    let name = firstName.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    let greeting = name.isEmpty ? "hi 🌱" : "hi \(name) 🌱"
    return "\(greeting) welcome to pda! use this link to sign in: \(url)"
}

func memberSmsLink(phone: String, message: String) -> String {
    let allowed = CharacterSet(charactersIn: "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_.!~*'()")
    let body = message.addingPercentEncoding(withAllowedCharacters: allowed) ?? message
    return "sms:\(phone)&body=\(body)"
}

extension EventsClient {
    func createMember(firstName: String, lastName: String, phone: String, email: String) async throws -> CreatedMember {
        let first = firstName.trimmingCharacters(in: .whitespacesAndNewlines)
        let last = lastName.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPhone = phone.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines)
        var payload: [String: String] = [
            "phone_number": trimmedPhone,
            "email": trimmedEmail,
        ]
        if !first.isEmpty { payload["first_name"] = first }
        if !last.isEmpty { payload["last_name"] = last }
        var req = URLRequest(url: createMemberURL(base: baseURL))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: payload)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw MemberCreateError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(CreatedMember.self, from: data)
    }
}

@Observable
final class MemberCreateModel {
    var client: EventsClient
    var firstName = ""
    var lastName = ""
    var phone = ""
    var email = ""
    var formError: String?
    var forbidden = false
    var created: CreatedMember?
    var copied = false
    var closed = false
    var saving = false

    var explanationTitle: String { MemberCreateCopy.forbiddenTitle }
    var explanationBody: String { MemberCreateCopy.forbiddenBody }
    var welcomeBody: String { MemberCreateCopy.welcomeBody }
    var copyLabel: String { copied ? MemberCreateCopy.copied : MemberCreateCopy.copyLink }

    var welcomeTitle: String {
        guard let created else { return "" }
        return memberWelcomeTitle(fullName: created.fullName, phone: created.phoneNumber)
    }

    var magicLink: String {
        guard let created else { return "" }
        return magicLoginURL(base: client.baseURL, token: created.magicLinkToken)
    }

    var smsLink: String {
        guard let created else { return "" }
        return memberSmsLink(
            phone: created.phoneNumber,
            message: memberWelcomeMessage(firstName: created.firstName, url: magicLink)
        )
    }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func submit() async -> Bool {
        formError = nil
        let first = firstName.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPhone = phone.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines)
        if first.isEmpty {
            formError = MemberCreateCopy.firstNameRequired
            return false
        }
        if trimmedPhone.isEmpty {
            formError = MemberCreateCopy.phoneRequired
            return false
        }
        if trimmedEmail.isEmpty {
            formError = MemberCreateCopy.emailRequired
            return false
        }
        saving = true
        defer { saving = false }
        do {
            created = try await client.createMember(
                firstName: firstName,
                lastName: lastName,
                phone: phone,
                email: email
            )
            return true
        } catch MemberCreateError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = MemberCreateCopy.failure
            return false
        }
    }

    func copyLink() {
        copied = true
    }

    func done() {
        firstName = ""
        lastName = ""
        phone = ""
        email = ""
        formError = nil
        created = nil
        copied = false
        forbidden = false
        closed = true
    }
}

struct MemberCreateView: View {
    var client: EventsClient
    @Environment(\.dismiss) private var dismiss
    @State private var model: MemberCreateModel?

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
            } else if let model, model.created != nil {
                welcome(model)
            } else if let model {
                form(model)
            }
        }
        .navigationTitle(model?.created == nil ? MemberCreateCopy.title : (model?.welcomeTitle ?? MemberCreateCopy.title))
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if model?.created == nil, model?.forbidden != true {
                ToolbarItem(placement: .cancellationAction) {
                    Button(MemberCreateCopy.cancel) { dismiss() }
                }
            }
        }
        .task {
            if model == nil { model = MemberCreateModel(client: client) }
        }
    }

    private func form(_ model: MemberCreateModel) -> some View {
        Form {
            TextField(MemberCreateCopy.firstName, text: binding(model, \.firstName))
                .textInputAutocapitalization(.words)
            TextField(MemberCreateCopy.lastName, text: binding(model, \.lastName))
                .textInputAutocapitalization(.words)
            TextField(MemberCreateCopy.phone, text: binding(model, \.phone))
                .keyboardType(.phonePad)
            TextField(MemberCreateCopy.email, text: binding(model, \.email))
                .textInputAutocapitalization(.never)
                .keyboardType(.emailAddress)
                .autocorrectionDisabled()
            if let formError = model.formError {
                Text(formError).foregroundStyle(.red)
            }
            Button(model.saving ? MemberCreateCopy.creating : MemberCreateCopy.create) {
                Task { _ = await model.submit() }
            }
            .disabled(model.saving)
        }
    }

    private func welcome(_ model: MemberCreateModel) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(model.welcomeBody).foregroundStyle(.secondary)
            Text(model.magicLink).font(.footnote).textSelection(.enabled)
            HStack {
                Button(model.copyLabel) {
                    UIPasteboard.general.string = model.magicLink
                    model.copyLink()
                }
                if let url = URL(string: model.smsLink) {
                    Link(MemberCreateCopy.sendWelcome, destination: url)
                }
            }
            Spacer()
            Button(MemberCreateCopy.done) {
                model.done()
                dismiss()
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func binding(_ model: MemberCreateModel, _ keyPath: ReferenceWritableKeyPath<MemberCreateModel, String>) -> Binding<String> {
        Binding(get: { model[keyPath: keyPath] }, set: { model[keyPath: keyPath] = $0 })
    }
}
