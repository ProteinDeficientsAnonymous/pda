import SwiftUI

enum AdminMemberDetailCopy {
    static let notFound = "member not found"
    static let error = "couldn't load members — try refreshing"
    static let bio = "bio"
}

enum PauseAccountCopy {
    static let label = "pause account"
    static let paused = "member paused ✓"
    static let unpaused = "member unpaused ✓"
    static let adminsCantBePaused = "admins can't be paused"
    static let cannotPauseSelf = "you can't pause your own account"
    static let forbiddenTitle = "pause account"
    static let forbiddenBody = "you need permission to manage users to pause this account."
}

enum PauseAccountError: Error, Equatable {
    case forbidden
    case cannotPauseSelf
}

func pauseMemberURL(base: URL, id: String) -> URL {
    URL(string: "/api/auth/users/\(id)/", relativeTo: base)!.absoluteURL
}

func showsPauseAccount(_ user: SessionUser?) -> Bool {
    guard let user else { return false }
    return user.isAdmin || user.permissions.contains("manage_users")
}

func memberIsDefaultAdmin(_ member: AdminMember) -> Bool {
    member.roles.contains { $0.name == "admin" && $0.isDefault }
}

func adminMemberDetailTitle(_ member: AdminMember) -> String {
    if !member.fullName.isEmpty { return member.fullName }
    if !member.phoneNumber.isEmpty { return member.phoneNumber }
    return AdminMembersCopy.fallbackName
}

extension EventsClient {
    func adminMemberDetail(id: String) async throws -> AdminMember {
        guard let member = try await adminMembers().first(where: { $0.id == id }) else {
            throw AdminMembersError.notFound
        }
        return member
    }

    func setMemberPaused(id: String, paused: Bool) async throws {
        var req = URLRequest(url: pauseMemberURL(base: baseURL, id: id))
        req.httpMethod = "PATCH"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: ["is_paused": paused])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw PauseAccountError.forbidden }
        if status == 400, pauseErrorCode(data) == "user.cannot_pause_self" {
            throw PauseAccountError.cannotPauseSelf
        }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
    }
}

private func pauseErrorCode(_ data: Data) -> String? {
    let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    let detail = json?["detail"] as? [[String: Any]]
    return detail?.first?["code"] as? String
}

@Observable
final class AdminMemberDetailModel {
    var client: EventsClient
    var member: AdminMember?
    var forbidden = false
    var error: String?
    var paused = false
    var toast: String?
    var formError: String?
    var pauseForbidden = false
    var saving = false

    var explanationTitle: String { AdminMembersCopy.forbiddenTitle }
    var explanationBody: String { AdminMembersCopy.forbiddenBody }
    var pauseExplanationTitle: String { PauseAccountCopy.forbiddenTitle }
    var pauseExplanationBody: String { PauseAccountCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load(id: String) async {
        error = nil
        forbidden = false
        member = nil
        paused = false
        do {
            member = try await client.adminMemberDetail(id: id)
            paused = member?.isPaused ?? false
        } catch AdminMembersError.forbidden {
            forbidden = true
        } catch AdminMembersError.notFound {
            error = AdminMemberDetailCopy.notFound
        } catch {
            self.error = AdminMemberDetailCopy.error
        }
    }

    func setPaused(_ next: Bool) async -> Bool {
        guard let member else { return false }
        if memberIsDefaultAdmin(member) { return false }
        formError = nil
        saving = true
        defer { saving = false }
        do {
            try await client.setMemberPaused(id: member.id, paused: next)
            paused = next
            toast = next ? PauseAccountCopy.paused : PauseAccountCopy.unpaused
            return true
        } catch PauseAccountError.forbidden {
            pauseForbidden = true
            toast = nil
            return false
        } catch PauseAccountError.cannotPauseSelf {
            formError = PauseAccountCopy.cannotPauseSelf
            toast = nil
            return false
        } catch {
            toast = nil
            return false
        }
    }
}

struct AdminMemberDetailView: View {
    let userId: String
    var client: EventsClient
    var canManageUsers = false
    @State private var model: AdminMemberDetailModel?

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
            } else if let model, model.pauseForbidden {
                VStack(alignment: .leading, spacing: 12) {
                    Text(model.pauseExplanationTitle).font(.title2)
                    Text(model.pauseExplanationBody).foregroundStyle(.secondary)
                    Spacer()
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
            } else if let model, let member = model.member {
                List {
                    Text(adminMemberDetailTitle(member).lowercased()).font(.headline)
                    if canManageUsers {
                        Toggle(PauseAccountCopy.label, isOn: Binding(
                            get: { model.paused },
                            set: { next in Task { await model.setPaused(next) } }
                        ))
                        .disabled(memberIsDefaultAdmin(member) || model.saving)
                        if memberIsDefaultAdmin(member) {
                            Text(PauseAccountCopy.adminsCantBePaused)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                        if let formError = model.formError {
                            Text(formError).foregroundStyle(.red)
                        }
                        if let toast = model.toast {
                            Text(toast).font(.footnote)
                        }
                    }
                    if !member.phoneNumber.isEmpty {
                        Text(member.phoneNumber.lowercased())
                    }
                    if !member.email.isEmpty {
                        Text(member.email.lowercased())
                    }
                    if !member.bio.isEmpty {
                        Section(AdminMemberDetailCopy.bio) {
                            Text(member.bio.lowercased())
                        }
                    }
                }
            } else if let model, let error = model.error {
                ContentUnavailableView {
                    Label(error, systemImage: "exclamationmark.triangle")
                } actions: {
                    Button("try again") { Task { await model.load(id: userId) } }
                }
            } else {
                ProgressView(AdminMembersCopy.loading)
            }
        }
        .navigationTitle(AdminMembersCopy.fallbackName)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = AdminMemberDetailModel(client: client) }
            await model?.load(id: userId)
        }
    }
}
