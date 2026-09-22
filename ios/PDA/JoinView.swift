import SwiftUI

enum JoinCopy {
    static let title = "request to join pda"
    static let subtitle =
        "we review all requests — you'll hear from us once a vetting member has had a look"
    static let requestToJoin = "request to join"
    static let firstName = "first name"
    static let lastName = "last name"
    static let phone = "phone number"
    static let phoneHint = "use the number you use (or will use) to connect with the community"
    static let email = "email"
    static let smsConsent =
        "i agree to pda's sms policy — i may receive event-related text messages and can reply stop to opt out."
    static let guidelinesConsent =
        "i have read and agree to the community guidelines and community agreements"
    static let submit = "submit request"
    static let submitting = "submitting…"
    static let loading = "loading…"
    static let error = "couldn't load the join form — try refreshing"
    static let successTitle = "request received!"
    static let successBody = "a vetting member will review your request and reach out soon"
    static let backHome = "back to home"
    static let firstNameRequired = "first name required"
    static let lastNameRequired = "last name required"
    static let phoneRequired = "phone required"
    static let emailRequired = "email required"
    static let emailInvalid = "not a valid email"
    static let smsRequired = "please agree to receive sms about events"
    static let guidelinesRequired =
        "please read and confirm you agree to the guidelines and community agreements"
    static let alreadyInvited = "you already have an account — sign in"
    static let signIn = "sign in"
}

enum JoinError: Error, Equatable {
    case alreadyInvited
}

enum JoinDestination: Equatable {
    case form, success, login
}

struct JoinQuestion: Decodable, Hashable, Identifiable {
    var id: String
    var label: String
    var fieldType: String
    var required: Bool
    var options: [String]
    var displayOrder: Int

    enum CodingKeys: String, CodingKey {
        case id, label, required, options
        case fieldType = "field_type"
        case displayOrder = "display_order"
    }

    init(
        id: String,
        label: String,
        fieldType: String,
        required: Bool,
        options: [String],
        displayOrder: Int
    ) {
        self.id = id
        self.label = label
        self.fieldType = fieldType
        self.required = required
        self.options = options
        self.displayOrder = displayOrder
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        label = try c.decodeIfPresent(String.self, forKey: .label) ?? ""
        fieldType = try c.decodeIfPresent(String.self, forKey: .fieldType) ?? "text"
        required = try c.decodeIfPresent(Bool.self, forKey: .required) ?? false
        options = try c.decodeIfPresent([String].self, forKey: .options) ?? []
        displayOrder = try c.decodeIfPresent(Int.self, forKey: .displayOrder) ?? 0
    }
}

func joinFormURL(base: URL) -> URL {
    URL(string: "/api/community/join-form/", relativeTo: base)!.absoluteURL
}

func joinRequestURL(base: URL) -> URL {
    URL(string: "/api/community/join-request/", relativeTo: base)!.absoluteURL
}

@Observable
final class JoinModel {
    var client: EventsClient
    var firstName = ""
    var lastName = ""
    var phone = ""
    var email = ""
    var answers: [String: String] = [:]
    var smsConsent = false
    var guidelinesConsent = false
    var questions: [JoinQuestion] = []
    var errors: [String: String] = [:]
    var serverError: String?
    var destination: JoinDestination = .form
    var busy = false
    var loadError: String?
    var loaded = false

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        loadError = nil
        do {
            questions = try await client.joinForm()
            for question in questions where answers[question.id] == nil {
                answers[question.id] = ""
            }
        } catch {
            loadError = JoinCopy.error
        }
        loaded = true
    }

    func submit() async {
        serverError = nil
        guard validate() else { return }
        busy = true
        defer { busy = false }
        let nonempty = answers.filter { !$0.value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        do {
            try await client.submitJoinRequest(
                firstName: firstName.trimmingCharacters(in: .whitespacesAndNewlines),
                lastName: lastName.trimmingCharacters(in: .whitespacesAndNewlines),
                phone: phone.trimmingCharacters(in: .whitespacesAndNewlines),
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                answers: nonempty,
                smsConsent: smsConsent,
                guidelinesConsent: guidelinesConsent
            )
            destination = .success
        } catch JoinError.alreadyInvited {
            destination = .login
        } catch {
            serverError = JoinCopy.error
        }
    }

    private func validate() -> Bool {
        var next: [String: String] = [:]
        if firstName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            next["firstName"] = JoinCopy.firstNameRequired
        }
        if lastName.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            next["lastName"] = JoinCopy.lastNameRequired
        }
        if phone.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
            next["phone"] = JoinCopy.phoneRequired
        }
        let mail = email.trimmingCharacters(in: .whitespacesAndNewlines)
        if mail.isEmpty {
            next["email"] = JoinCopy.emailRequired
        } else if !isJoinEmail(mail) {
            next["email"] = JoinCopy.emailInvalid
        }
        if !smsConsent { next["smsConsent"] = JoinCopy.smsRequired }
        if !guidelinesConsent { next["guidelinesConsent"] = JoinCopy.guidelinesRequired }
        for question in questions {
            let val = (answers[question.id] ?? "").trimmingCharacters(in: .whitespacesAndNewlines)
            if question.required, val.isEmpty {
                next[question.id] = "required"
            } else if val.count > 2000 {
                next[question.id] = "under 2000 chars"
            }
        }
        errors = next
        return next.isEmpty
    }
}

func isJoinEmail(_ raw: String) -> Bool {
    let parts = raw.split(separator: "@", maxSplits: 1, omittingEmptySubsequences: false)
    guard parts.count == 2, !parts[0].isEmpty, !parts[1].isEmpty else { return false }
    return parts[1].contains(".") && !raw.contains(" ")
}

struct JoinView: View {
    var onSignIn: () -> Void = {}
    var onHome: () -> Void = {}
    @Environment(\.dismiss) private var dismiss
    @State private var model: JoinModel
    @State private var showGuidelines = false

    init(
        client: EventsClient = EventsClient(),
        onSignIn: @escaping () -> Void = {},
        onHome: @escaping () -> Void = {}
    ) {
        self.onSignIn = onSignIn
        self.onHome = onHome
        _model = State(initialValue: JoinModel(client: client))
    }

    var body: some View {
        NavigationStack {
            Group {
                switch model.destination {
                case .success:
                    success
                case .login:
                    alreadyInvited
                case .form:
                    form
                }
            }
            .navigationTitle(model.destination == .success ? JoinCopy.successTitle : JoinCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton("close", variant: .secondary) { dismiss() }
                }
            }
            .task { await model.load() }
            .sheet(isPresented: $showGuidelines) {
                GuidelinesView()
            }
        }
    }

    private var form: some View {
        Group {
            if let loadError = model.loadError {
                ContentUnavailableView {
                    Label(loadError, systemImage: "exclamationmark.triangle")
                } actions: {
                    PDAButton("try again") { Task { await model.load() } }
                }
            } else if !model.loaded {
                ProgressView(JoinCopy.loading)
            } else {
                formFields
            }
        }
    }

    private var formFields: some View {
        Form {
            Section {
                Text(JoinCopy.subtitle)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Section {
                labeledField(JoinCopy.firstName, text: $model.firstName, error: model.errors["firstName"])
                    .textContentType(.givenName)
                labeledField(JoinCopy.lastName, text: $model.lastName, error: model.errors["lastName"])
                    .textContentType(.familyName)
                labeledField(JoinCopy.phone, text: $model.phone, error: model.errors["phone"])
                    .keyboardType(.phonePad)
                    .textContentType(.telephoneNumber)
                Text(JoinCopy.phoneHint)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                labeledField(JoinCopy.email, text: $model.email, error: model.errors["email"])
                    .keyboardType(.emailAddress)
                    .textContentType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
            }
            if !model.questions.isEmpty {
                Section {
                    ForEach(model.questions) { question in
                        questionField(question)
                    }
                }
            }
            Section {
                Toggle(JoinCopy.smsConsent, isOn: $model.smsConsent)
                if let error = model.errors["smsConsent"] {
                    Text(error).font(.footnote).foregroundStyle(.red)
                }
                Toggle(JoinCopy.guidelinesConsent, isOn: $model.guidelinesConsent)
                PDAButton(GuidelinesCopy.title, variant: .ghost) { showGuidelines = true }
                if let error = model.errors["guidelinesConsent"] {
                    Text(error).font(.footnote).foregroundStyle(.red)
                }
            }
            if let serverError = model.serverError {
                Section {
                    Text(serverError).font(.footnote).foregroundStyle(.red)
                }
            }
            Section {
                PDAButton(model.busy ? JoinCopy.submitting : JoinCopy.submit) {
                    Task { await model.submit() }
                }
                .disabled(model.busy)
            }
        }
    }

    private var success: some View {
        VStack(spacing: 16) {
            Text("🌱").font(.largeTitle)
            Text(JoinCopy.successTitle).font(.title2)
            Text(JoinCopy.successBody)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            PDAButton(JoinCopy.backHome, variant: .secondary) {
                onHome()
                dismiss()
            }
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .center)
    }

    private var alreadyInvited: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(JoinCopy.alreadyInvited)
            PDAButton(JoinCopy.signIn) {
                onSignIn()
                dismiss()
            }
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
    }

    private func labeledField(_ label: String, text: Binding<String>, error: String?) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            PDATextField(label, text: text)
            if let error {
                Text(error).font(.footnote).foregroundStyle(.red)
            }
        }
    }

    @ViewBuilder
    private func questionField(_ question: JoinQuestion) -> some View {
        let label = question.required ? question.label : "\(question.label) (optional)"
        VStack(alignment: .leading, spacing: 4) {
            switch question.fieldType {
            case "select":
                Picker(label, selection: answerBinding(question.id)) {
                    Text("select one").tag("")
                    ForEach(question.options, id: \.self) { option in
                        Text(option.lowercased()).tag(option)
                    }
                }
            case "textarea":
                PDATextField(
                    label,
                    text: answerBinding(question.id),
                    axis: .vertical,
                    capitalization: .never,
                    lineLimit: 5,
                    reserveLineSpace: true
                )
            default:
                PDATextField(label, text: answerBinding(question.id), capitalization: .never)
            }
            if let error = model.errors[question.id] {
                Text(error).font(.footnote).foregroundStyle(.red)
            }
        }
    }

    private func answerBinding(_ id: String) -> Binding<String> {
        Binding(get: { model.answers[id] ?? "" }, set: { model.answers[id] = $0 })
    }
}
