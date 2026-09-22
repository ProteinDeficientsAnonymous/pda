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

enum MagicLoginCopy {
    static let button = "generate magic login link"
    static let working = "working…"
    static let copyLink = "copy link"
    static let copied = "copied ✓"
    static let sendWelcome = "send welcome message"
    static let hint = "resets password flow for this member and generates a one-time login url for you to send them."
    static let forbiddenTitle = "generate magic login link"
    static let forbiddenBody = "you need permission to manage users to generate a login link."
}

enum MagicLoginError: Error, Equatable {
    case forbidden
}

struct MagicLoginResult: Decodable {
    let magicLinkToken: String

    enum CodingKeys: String, CodingKey {
        case magicLinkToken = "magic_link_token"
    }
}

func magicLoginLinkURL(base: URL, id: String) -> URL {
    URL(string: "/api/auth/users/\(id)/magic-link/", relativeTo: base)!.absoluteURL
}

func showsMagicLoginLink(_ user: SessionUser?) -> Bool {
    guard let user else { return false }
    return user.isAdmin || user.permissions.contains("manage_users")
}

enum MemberProfileEditCopy {
    static let edit = "edit"
    static let cancel = "cancel"
    static let save = "save"
    static let saving = "saving…"
    static let firstName = "first name"
    static let lastName = "last name (optional)"
    static let phone = "phone number"
    static let email = "email"
    static let firstNameRequired = "first name required"
    static let saved = "member updated ✓"
    static let error = "couldn't save changes — try again"
}

func showsMemberProfileEdit(_ user: SessionUser?) -> Bool {
    guard let user else { return false }
    return user.isAdmin || user.permissions.contains("manage_users")
}

enum MemberRolesCopy {
    static let title = "roles"
    static let loading = "loading roles…"
    static let save = "save roles"
    static let saving = "saving…"
    static let saved = "roles updated ✓"
    static let error = "couldn't save changes — try again"
}

func memberRoleLocked(_ role: AdminRole, viewerIsAdmin: Bool) -> Bool {
    role.name == "admin" && role.isDefault && !viewerIsAdmin
}

func memberRolesURL(base: URL, id: String) -> URL {
    URL(string: "/api/auth/users/\(id)/roles/", relativeTo: base)!.absoluteURL
}

func magicLoginButtonLabel(working: Bool) -> String {
    working ? MagicLoginCopy.working : MagicLoginCopy.button
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

    func generateMagicLoginLink(id: String) async throws -> String {
        var req = URLRequest(url: magicLoginLinkURL(base: baseURL, id: id))
        req.httpMethod = "POST"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw MagicLoginError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(MagicLoginResult.self, from: data).magicLinkToken
    }

    func updateMemberProfile(id: String, body: [String: Any]) async throws -> AdminMember {
        var req = URLRequest(url: pauseMemberURL(base: baseURL, id: id))
        req.httpMethod = "PATCH"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(AdminMember.self, from: data)
    }

    func updateMemberRoles(id: String, roleIDs: [String]) async throws -> AdminMember {
        var req = URLRequest(url: memberRolesURL(base: baseURL, id: id))
        req.httpMethod = "PATCH"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: ["role_ids": roleIDs])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(AdminMember.self, from: data)
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
    var magicLink: String?
    var magicCopied = false
    var magicWorking = false
    var magicForbidden = false
    var editingProfile = false
    var profileFirstName = ""
    var profileLastName = ""
    var profilePhone = ""
    var profileEmail = ""
    var profilePaused = false
    var profileError: String?
    var profileSaving = false
    var roleCatalog: [AdminRole] = []
    var selectedRoleIDs: Set<String> = []
    var rolesUnavailable = false
    var rolesLoaded = false
    var rolesError: String?
    var rolesSaving = false

    var rolesUnchanged: Bool {
        selectedRoleIDs == Set(member?.roles.map(\.id) ?? [])
    }

    var explanationTitle: String { AdminMembersCopy.forbiddenTitle }
    var explanationBody: String { AdminMembersCopy.forbiddenBody }
    var pauseExplanationTitle: String { PauseAccountCopy.forbiddenTitle }
    var pauseExplanationBody: String { PauseAccountCopy.forbiddenBody }
    var magicCopyLabel: String { magicCopied ? MagicLoginCopy.copied : MagicLoginCopy.copyLink }
    var magicExplanationTitle: String { MagicLoginCopy.forbiddenTitle }
    var magicExplanationBody: String { MagicLoginCopy.forbiddenBody }

    var welcomeMessage: String {
        guard let magicLink, let member else { return "" }
        return memberWelcomeMessage(firstName: member.firstName, url: magicLink)
    }

    var smsLink: String {
        guard let member, !welcomeMessage.isEmpty else { return "" }
        return memberSmsLink(phone: member.phoneNumber, message: welcomeMessage)
    }

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

    func generateMagicLink() async -> Bool {
        guard let member else { return false }
        magicWorking = true
        defer { magicWorking = false }
        do {
            let token = try await client.generateMagicLoginLink(id: member.id)
            magicLink = magicLoginURL(base: client.baseURL, token: token)
            return true
        } catch MagicLoginError.forbidden {
            magicForbidden = true
            return false
        } catch {
            return false
        }
    }

    func copyMagicLink() {
        magicCopied = true
    }

    func beginProfileEdit() {
        guard let member else { return }
        profileFirstName = member.firstName
        profileLastName = member.lastName
        profilePhone = member.phoneNumber
        profileEmail = member.email
        profilePaused = member.isPaused
        profileError = nil
        editingProfile = true
    }

    func cancelProfileEdit() {
        editingProfile = false
        profileError = nil
    }

    func saveProfile() async {
        guard let member else { return }
        let nextFirstName = profileFirstName.trimmingCharacters(in: .whitespacesAndNewlines)
        if nextFirstName.isEmpty {
            profileError = MemberProfileEditCopy.firstNameRequired
            return
        }
        var body: [String: Any] = [:]
        if nextFirstName != member.firstName { body["first_name"] = nextFirstName }
        let lastName = profileLastName.trimmingCharacters(in: .whitespacesAndNewlines)
        if lastName != member.lastName { body["last_name"] = lastName }
        if profilePhone != member.phoneNumber {
            body["phone_number"] = profilePhone.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        if profileEmail != member.email {
            body["email"] = profileEmail.trimmingCharacters(in: .whitespacesAndNewlines)
        }
        if !memberIsDefaultAdmin(member), profilePaused != member.isPaused {
            body["is_paused"] = profilePaused
        }
        if body.isEmpty {
            editingProfile = false
            return
        }
        profileSaving = true
        defer { profileSaving = false }
        profileError = nil
        do {
            let updated = try await client.updateMemberProfile(id: member.id, body: body)
            self.member = updated
            paused = updated.isPaused
            toast = MemberProfileEditCopy.saved
            editingProfile = false
        } catch {
            profileError = MemberProfileEditCopy.error
        }
    }

    func loadRoles() async {
        do {
            roleCatalog = try await client.adminRoles()
            selectedRoleIDs = Set(member?.roles.map(\.id) ?? [])
            rolesUnavailable = false
            rolesError = nil
            rolesLoaded = true
        } catch {
            roleCatalog = []
            rolesUnavailable = true
            rolesError = nil
            rolesLoaded = true
        }
    }

    func toggleRole(_ role: AdminRole, viewerIsAdmin: Bool) {
        guard !memberRoleLocked(role, viewerIsAdmin: viewerIsAdmin) else { return }
        if selectedRoleIDs.contains(role.id) {
            selectedRoleIDs.remove(role.id)
        } else {
            selectedRoleIDs.insert(role.id)
        }
    }

    func saveRoles() async {
        guard let member, !rolesUnchanged else { return }
        rolesSaving = true
        defer { rolesSaving = false }
        rolesError = nil
        do {
            let updated = try await client.updateMemberRoles(id: member.id, roleIDs: Array(selectedRoleIDs))
            self.member = updated
            selectedRoleIDs = Set(updated.roles.map(\.id))
            toast = MemberRolesCopy.saved
        } catch {
            rolesError = MemberRolesCopy.error
        }
    }
}

struct AdminMemberDetailView: View {
    let userId: String
    var client: EventsClient
    var canManageUsers = false
    var viewerIsAdmin = false
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
            } else if let model, model.magicForbidden {
                VStack(alignment: .leading, spacing: 12) {
                    Text(model.magicExplanationTitle).font(.title2)
                    Text(model.magicExplanationBody).foregroundStyle(.secondary)
                    Spacer()
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
            } else if let model, let member = model.member {
                List {
                    Text(adminMemberDetailTitle(member).lowercased()).font(.headline)
                    if canManageUsers {
                        rolesSection(model)
                    }
                    if canManageUsers, model.editingProfile {
                        profileEditor(model)
                    } else if canManageUsers {
                        PDAButton(MemberProfileEditCopy.edit) { model.beginProfileEdit() }
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
                        if let toast = model.toast, toast != MemberRolesCopy.saved {
                            Text(toast).font(.footnote)
                        }
                        if model.magicLink == nil {
                            PDAButton(magicLoginButtonLabel(working: model.magicWorking)) {
                                Task { _ = await model.generateMagicLink() }
                            }
                            .disabled(model.magicWorking)
                        } else {
                            Text(model.magicLink ?? "").font(.footnote).textSelection(.enabled)
                            PDAButton(model.magicCopyLabel, variant: .secondary) {
                                UIPasteboard.general.string = model.magicLink
                                model.copyMagicLink()
                            }
                            if let sms = URL(string: model.smsLink) {
                                Link(MagicLoginCopy.sendWelcome, destination: sms)
                            }
                        }
                        Text(MagicLoginCopy.hint)
                            .font(.footnote)
                            .foregroundStyle(.secondary)
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
                    PDAButton("try again") { Task { await model.load(id: userId) } }
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
            if model?.member != nil { await model?.loadRoles() }
        }
    }

    @ViewBuilder
    private func rolesSection(_ model: AdminMemberDetailModel) -> some View {
        if model.rolesUnavailable {
            EmptyView()
        } else if !model.rolesLoaded {
            Text(MemberRolesCopy.loading)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
        } else {
            Section {
                ForEach(model.roleCatalog) { role in
                    Toggle(
                        role.name,
                        isOn: Binding(
                            get: { model.selectedRoleIDs.contains(role.id) },
                            set: { _ in model.toggleRole(role, viewerIsAdmin: viewerIsAdmin) }
                        )
                    )
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foreground)
                    .tint(PDAColor.brand600)
                    .disabled(memberRoleLocked(role, viewerIsAdmin: viewerIsAdmin) || model.rolesSaving)
                }
                if let rolesError = model.rolesError {
                    Text(rolesError)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.destructive)
                }
                if model.toast == MemberRolesCopy.saved {
                    Text(MemberRolesCopy.saved)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.muted)
                }
                PDAButton(
                    model.rolesSaving ? MemberRolesCopy.saving : MemberRolesCopy.save,
                    variant: .secondary
                ) {
                    Task { await model.saveRoles() }
                }
                .disabled(model.rolesUnchanged || model.rolesSaving)
            } header: {
                Text(MemberRolesCopy.title)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.muted)
                    .textCase(nil)
            }
        }
    }

    @ViewBuilder
    private func profileEditor(_ model: AdminMemberDetailModel) -> some View {
        PDATextField(MemberProfileEditCopy.firstName, text: Bindable(model).profileFirstName, capitalization: .words)
        PDATextField(MemberProfileEditCopy.lastName, text: Bindable(model).profileLastName, capitalization: .words)
        PDATextField(
            MemberProfileEditCopy.phone,
            text: Bindable(model).profilePhone,
            keyboard: .phonePad,
            contentType: .telephoneNumber
        )
        PDATextField(
            MemberProfileEditCopy.email,
            text: Bindable(model).profileEmail,
            capitalization: .never,
            disableAutocorrection: true,
            keyboard: .emailAddress,
            contentType: .emailAddress
        )
        if let member = model.member {
            Toggle(PauseAccountCopy.label, isOn: Bindable(model).profilePaused)
                .disabled(memberIsDefaultAdmin(member) || model.profileSaving)
            if memberIsDefaultAdmin(member) {
                Text(PauseAccountCopy.adminsCantBePaused)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.muted)
            }
        }
        if let profileError = model.profileError {
            Text(profileError)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.destructive)
        }
        HStack {
            PDAButton(MemberProfileEditCopy.cancel, variant: .ghost) { model.cancelProfileEdit() }
            PDAButton(model.profileSaving ? MemberProfileEditCopy.saving : MemberProfileEditCopy.save) {
                Task { await model.saveProfile() }
            }
            .disabled(model.profileSaving)
        }
    }
}
