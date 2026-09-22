import SwiftUI

enum MagicConsumeError: Error {
    case crossUser
    case expired
}

enum MagicConsumeState: Equatable {
    case pending
    case ready(AuthGate?)
    case expired
    case crossUser
}

enum MagicConsumeCopy {
    static let signingIn = "signing you in…"
    static let holdTight = "hold tight 🌿"
    static let expiredTitle = "link expired"
    static let expiredSubtitle = "this login link didn't work"
    static let signInWithPassword = "sign in with your password"
    static let alreadySignedIn = "already signed in"
    static let differentAccount = "this link is for a different account"
    static let logOutFirst = "log out first, then open the link again"
    static let backToCalendar = "back to calendar"
}

func magicLoginToken(from url: URL) -> String? {
    let parts = url.path.split(separator: "/").map(String.init)
    guard parts.count >= 2, parts[parts.count - 2] == "magic-login" else { return nil }
    let token = parts[parts.count - 1]
    guard !token.isEmpty else { return nil }
    return token.removingPercentEncoding ?? token
}

@Observable
final class MagicConsumeModel {
    private(set) var state: MagicConsumeState = .pending
    private(set) var user: SessionUser?
    private var firedFor: String?
    let token: String
    let client: SessionClient

    init(token: String, client: SessionClient) {
        self.token = token
        self.client = client
    }

    func consume() async {
        if firedFor == token { return }
        firedFor = token
        do {
            let user = try await client.consumeMagicLogin(token)
            self.user = user
            state = .ready(authGate(for: user))
        } catch MagicConsumeError.crossUser {
            state = .crossUser
        } catch {
            state = .expired
        }
    }

    func apply(to session: AuthSession) -> Bool {
        guard case .ready = state, let user else { return false }
        session.signedIn(user)
        return true
    }
}

struct MagicLoginView: View {
    @Environment(\.dismiss) private var dismiss
    @Environment(AuthSession.self) private var session
    @State private var model: MagicConsumeModel
    private let onSignIn: () -> Void

    init(token: String, client: SessionClient, onSignIn: @escaping () -> Void) {
        _model = State(initialValue: MagicConsumeModel(token: token, client: client))
        self.onSignIn = onSignIn
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 16) {
                switch model.state {
                case .pending, .ready:
                    Text(MagicConsumeCopy.signingIn)
                        .font(PDAType.field)
                        .fontWeight(.medium)
                        .foregroundStyle(PDAColor.foreground)
                    Text(MagicConsumeCopy.holdTight)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.muted)
                case .expired:
                    Text(MagicConsumeCopy.expiredTitle)
                        .font(PDAType.field)
                        .fontWeight(.medium)
                        .foregroundStyle(PDAColor.foreground)
                    Text(MagicConsumeCopy.expiredSubtitle)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.foregroundTertiary)
                    PDAButton(MagicConsumeCopy.signInWithPassword) {
                        onSignIn()
                        dismiss()
                    }
                case .crossUser:
                    Text(MagicConsumeCopy.alreadySignedIn)
                        .font(PDAType.field)
                        .fontWeight(.medium)
                        .foregroundStyle(PDAColor.foreground)
                    Text(MagicConsumeCopy.differentAccount)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.foregroundSecondary)
                    Text(MagicConsumeCopy.logOutFirst)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.foregroundTertiary)
                    PDAButton(MagicConsumeCopy.backToCalendar) { dismiss() }
                }
            }
            .padding(16)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(PDAColor.background)
        }
        .task {
            await model.consume()
            if model.apply(to: session) { dismiss() }
        }
    }
}
