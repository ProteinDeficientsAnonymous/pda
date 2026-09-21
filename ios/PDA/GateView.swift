import SwiftUI

struct GateView: View {
    @Environment(AuthSession.self) private var session
    @State private var password = ""
    @State private var confirm = ""
    @State private var firstName = ""
    @State private var email = ""
    @State private var agreeGuidelines = false
    @State private var agreeSms = false
    @State private var agreePrivacy = false
    @State private var error: String?
    @State private var busy = false

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                if let user = session.user, let gate = authGate(for: user) {
                    switch gate {
                    case .newPassword: newPasswordForm
                    case .onboarding: onboardingForm
                    case .consent: consentForm(user)
                    case .email: emailForm
                    }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text(title).font(.headline)
                }
            }
            .onAppear {
                firstName = session.user?.firstName ?? ""
                email = session.user?.email ?? ""
            }
        }
    }

    private var title: String {
        switch authGate(for: session.user) {
        case .newPassword: GateCopy.newPasswordTitle
        case .onboarding: GateCopy.onboardingTitle
        case .consent: GateCopy.consentTitle
        case .email: GateCopy.emailTitle
        case nil: ""
        }
    }

    private var newPasswordForm: some View {
        form {
            SecureField(GateCopy.newPasswordLabel, text: $password)
            SecureField(GateCopy.confirmPasswordLabel, text: $confirm)
            if let error { Text(error).font(.footnote).foregroundStyle(.red) }
            Button(GateCopy.savePassword) { Task { await saveNewPassword() } }
                .buttonStyle(.borderedProminent)
                .disabled(busy || !passwordIsValid(password) || password != confirm)
        }
    }

    private var onboardingForm: some View {
        form {
            TextField(GateCopy.firstNameLabel, text: $firstName)
                .textInputAutocapitalization(.never)
            TextField(GateCopy.emailLabel, text: $email)
                .keyboardType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            SecureField(GateCopy.newPasswordLabel, text: $password)
            Toggle(GateCopy.agreeGuidelines, isOn: $agreeGuidelines)
            Toggle(GateCopy.agreeSms, isOn: $agreeSms)
            if let error { Text(error).font(.footnote).foregroundStyle(.red) }
            Button(GateCopy.continueButton) { Task { await saveOnboarding() } }
                .buttonStyle(.borderedProminent)
                .disabled(busy || firstName.isEmpty || email.isEmpty || !passwordIsValid(password) || !agreeGuidelines || !agreeSms)
        }
    }

    private func consentForm(_ user: SessionUser) -> some View {
        form {
            if user.needsGuidelinesConsent {
                Toggle(GateCopy.agreeGuidelines, isOn: $agreeGuidelines)
            }
            if user.needsSmsConsent {
                Toggle(GateCopy.agreeSms, isOn: $agreeSms)
            }
            if user.needsContactPrivacyConsent {
                Toggle(GateCopy.agreePrivacy, isOn: $agreePrivacy)
            }
            if let error { Text(error).font(.footnote).foregroundStyle(.red) }
            Button(GateCopy.continueButton) { Task { await saveConsents(user) } }
                .buttonStyle(.borderedProminent)
                .disabled(busy || !consentsReady(user))
            Button(GateCopy.notNow) { Task { await session.logout() } }
                .disabled(busy)
        }
    }

    private var emailForm: some View {
        form {
            Text(GateCopy.emailBody).font(.subheadline).foregroundStyle(.secondary)
            TextField(GateCopy.emailLabel, text: $email)
                .keyboardType(.emailAddress)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
            if let error { Text(error).font(.footnote).foregroundStyle(.red) }
            Button(GateCopy.save) { Task { await saveEmail() } }
                .buttonStyle(.borderedProminent)
                .disabled(busy || email.isEmpty)
            Button(GateCopy.notNow) { Task { await session.logout() } }
                .disabled(busy)
        }
    }

    private func form(@ViewBuilder _ content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 16, content: content)
    }

    private func consentsReady(_ user: SessionUser) -> Bool {
        (!user.needsGuidelinesConsent || agreeGuidelines)
            && (!user.needsSmsConsent || agreeSms)
            && (!user.needsContactPrivacyConsent || agreePrivacy)
    }

    private func saveNewPassword() async {
        await run {
            session.signedIn(try await session.client.completeOnboarding(newPassword: password))
        }
    }

    private func saveOnboarding() async {
        await run {
            session.signedIn(
                try await session.client.completeOnboarding(
                    newPassword: password,
                    firstName: firstName,
                    email: email,
                    consentTypes: ["guidelines", "sms"]
                )
            )
        }
    }

    private func saveConsents(_ user: SessionUser) async {
        await run {
            var types: [String] = []
            if user.needsGuidelinesConsent { types.append("guidelines") }
            if user.needsSmsConsent { types.append("sms") }
            if user.needsContactPrivacyConsent { types.append("contact_privacy") }
            session.signedIn(try await session.client.acceptConsents(types))
        }
    }

    private func saveEmail() async {
        await run {
            session.signedIn(try await session.client.setEmail(email))
        }
    }

    private func run(_ work: () async throws -> Void) async {
        error = nil
        busy = true
        defer { busy = false }
        do {
            try await work()
        } catch let err as SessionError {
            error = err.message
        } catch {
            self.error = "couldn't save — try again"
        }
    }
}

func passwordIsValid(_ value: String) -> Bool {
    value.count >= 12
        && value.count <= 72
        && value.contains(where: \.isUppercase)
        && value.contains(where: \.isNumber)
        && value.contains(where: { !$0.isLetter && !$0.isNumber })
}
