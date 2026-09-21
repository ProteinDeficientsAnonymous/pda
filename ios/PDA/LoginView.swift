import SwiftUI

struct LoginView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(AuthSession.self) private var session
    @State private var model: LoginModel

    init(client: SessionClient) {
        _model = State(initialValue: LoginModel(client: client))
    }

    var body: some View {
        if model.step == .join {
            JoinView(
                client: EventsClient(baseURL: model.client.baseURL, session: model.client.session),
                onSignIn: { model.step = .phone },
                onHome: { dismiss() }
            )
        } else {
            NavigationStack {
                VStack(alignment: .leading, spacing: 16) {
                    switch model.step {
                    case .phone:
                        phoneStep
                    case .password:
                        passwordStep
                    case .pending:
                        statusStep(title: LoginCopy.pendingTitle, body: LoginCopy.pendingBody)
                    case .unknown:
                        statusStep(title: LoginCopy.unknownTitle, body: LoginCopy.unknownBody)
                    case .join:
                        EmptyView()
                    }
                }
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .principal) {
                        Text(LoginCopy.welcomeTitle).font(.headline)
                    }
                    ToolbarItem(placement: .cancellationAction) {
                        Button("close") { dismiss() }
                    }
                }
            }
        }
    }

    private var phoneStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(LoginCopy.welcomeSubtitle)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            TextField(LoginCopy.phoneLabel, text: $model.phone)
                .keyboardType(.phonePad)
                .textContentType(.username)
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .accessibilityIdentifier("phone-number")
            if let error = model.error {
                Text(error).font(.footnote).foregroundStyle(.red)
            }
            Button(LoginCopy.continueButton) {
                Task { await model.submitPhone() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(model.busy || model.phone.isEmpty)
            Button(JoinCopy.requestToJoin) {
                model.step = .join
            }
            .font(.subheadline)
        }
    }

    private var passwordStep: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(model.phone)
                .font(.subheadline)
                .foregroundStyle(.secondary)
            SecureField(LoginCopy.passwordLabel, text: $model.password)
                .textContentType(.password)
                .accessibilityIdentifier("password")
            if let error = model.error {
                Text(error).font(.footnote).foregroundStyle(.red)
            }
            Button(model.busy ? "signing in…" : LoginCopy.signInButton) {
                Task { await submitPassword() }
            }
            .buttonStyle(.borderedProminent)
            .disabled(model.busy || model.password.isEmpty)
            Button(LoginCopy.backButton) {
                model.step = .phone
                model.password = ""
                model.error = nil
            }
            .font(.subheadline)
        }
    }

    private func statusStep(title: String, body: String) -> some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(title).font(.title2)
            Text(body).font(.subheadline).foregroundStyle(.secondary)
            Button(LoginCopy.backButton) {
                model.step = .phone
                model.error = nil
            }
            .font(.subheadline)
        }
    }

    private func submitPassword() async {
        await model.signIn()
        guard model.error == nil, (try? model.client.tokens.load()) != nil else { return }
        do {
            session.signedIn(try await model.client.me())
            dismiss()
        } catch let error as SessionError {
            model.error = error.message
        } catch {
            model.error = "couldn't sign in — try again"
        }
    }
}
