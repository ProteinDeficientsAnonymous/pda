import SwiftUI

enum AdminRolesCopy {
    static let title = "roles"
    static let loading = "loading…"
    static let error = "couldn't load roles — try refreshing"
    static let empty = "no roles yet"
    static let forbiddenTitle = "roles"
    static let forbiddenBody = "you need permission to manage roles to see this list."
}

enum AdminRolesError: Error, Equatable {
    case forbidden
}

struct AdminRole: Decodable, Equatable, Identifiable {
    let id: String
    let name: String
    let permissions: [String]
    let userCount: Int
    let isDefault: Bool

    enum CodingKeys: String, CodingKey {
        case id, name, permissions
        case userCount = "user_count"
        case isDefault = "is_default"
    }

    init(id: String, name: String, permissions: [String], userCount: Int, isDefault: Bool = false) {
        self.id = id
        self.name = name
        self.permissions = permissions
        self.userCount = userCount
        self.isDefault = isDefault
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        permissions = try c.decodeIfPresent([String].self, forKey: .permissions) ?? []
        userCount = try c.decodeIfPresent(Int.self, forKey: .userCount) ?? 0
        isDefault = try c.decodeIfPresent(Bool.self, forKey: .isDefault) ?? false
    }
}

func adminRolesURL(base: URL) -> URL {
    URL(string: "/api/auth/roles/", relativeTo: base)!.absoluteURL
}

func adminRoleName(_ role: AdminRole) -> String {
    role.name.lowercased()
}

func adminRoleSubtitle(_ role: AdminRole) -> String {
    let permissions = role.permissions.count == 0
        ? "no permissions"
        : "\(role.permissions.count) permission\(role.permissions.count == 1 ? "" : "s")"
    let members = role.userCount == 0
        ? "no members"
        : "\(role.userCount) member\(role.userCount == 1 ? "" : "s")"
    return "\(permissions) · \(members)"
}

func adminMembersTabs(showRoles: Bool) -> [String] {
    showRoles ? ["members", "roles"] : ["members"]
}

func showsAdminRolesTab(_ user: SessionUser?) -> Bool {
    guard let user else { return false }
    return user.isAdmin || user.permissions.contains("manage_roles")
}

enum RoleDeleteCopy {
    static let button = "delete"
    static let title = "delete role"
    static let confirm = "delete"
    static let cancel = "cancel"
    static let failure = "couldn't delete role — try again"
    static let forbiddenTitle = "delete role"
    static let forbiddenBody = "you need permission to manage roles to delete this role."
}

struct RoleDeletePrompt: Equatable {
    let title: String
    let message: String
    let confirmLabel: String
}

enum RoleDeleteError: Error {
    case forbidden
}

func showsRoleDelete(_ role: AdminRole) -> Bool {
    !["admin", "member"].contains(role.name.lowercased())
}

func roleDeleteMessage(_ role: AdminRole) -> String {
    let name = adminRoleName(role)
    if role.userCount == 0 {
        return "delete the \"\(name)\" role? this cannot be undone."
    }
    if role.userCount == 1 {
        return "1 member has the \"\(name)\" role — deleting will remove it from them. continue?"
    }
    return "\(role.userCount) members have the \"\(name)\" role — deleting will remove it from all of them. continue?"
}

func roleDeleteToast(_ role: AdminRole) -> String {
    "\(adminRoleName(role)) deleted ✓"
}

extension EventsClient {
    func adminRoles() async throws -> [AdminRole] {
        var req = URLRequest(url: adminRolesURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw AdminRolesError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([AdminRole].self, from: data)
    }

    func deleteRole(id: String) async throws {
        var req = URLRequest(url: updateRoleURL(base: baseURL, id: id))
        req.httpMethod = "DELETE"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (_, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw RoleDeleteError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
    }
}

@Observable
final class AdminRolesModel {
    var client: EventsClient
    var roles: [AdminRole] = []
    var forbidden = false
    var error: String?
    var loaded = false
    var pendingDelete: AdminRole?
    var toast: String?
    var deleteError: String?
    var deleteForbidden = false

    var explanationTitle: String { AdminRolesCopy.forbiddenTitle }
    var explanationBody: String { AdminRolesCopy.forbiddenBody }
    var deleteExplanationTitle: String { RoleDeleteCopy.forbiddenTitle }
    var deleteExplanationBody: String { RoleDeleteCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func prepareDelete(_ role: AdminRole) -> RoleDeletePrompt? {
        guard showsRoleDelete(role) else { return nil }
        pendingDelete = role
        return RoleDeletePrompt(
            title: RoleDeleteCopy.title,
            message: roleDeleteMessage(role),
            confirmLabel: RoleDeleteCopy.confirm
        )
    }

    func cancelDelete() {
        pendingDelete = nil
    }

    func commitDelete() async -> Bool {
        guard let role = pendingDelete else { return false }
        return await commitDelete(role)
    }

    func commitDelete(_ role: AdminRole) async -> Bool {
        pendingDelete = nil
        deleteError = nil
        deleteForbidden = false
        toast = nil
        do {
            try await client.deleteRole(id: role.id)
            roles.removeAll { $0.id == role.id }
            toast = roleDeleteToast(role)
            return true
        } catch RoleDeleteError.forbidden {
            deleteForbidden = true
            return false
        } catch {
            deleteError = RoleDeleteCopy.failure
            return false
        }
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            roles = try await client.adminRoles()
            loaded = true
        } catch AdminRolesError.forbidden {
            roles = []
            forbidden = true
            loaded = true
        } catch {
            roles = []
            self.error = AdminRolesCopy.error
            loaded = true
        }
    }
}

struct AdminRolesView: View {
    var client: EventsClient
    @State private var model: AdminRolesModel?
    @State private var addingRole = false
    @State private var editingRole: AdminRole?

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
                ContentUnavailableView {
                    Label(error, systemImage: "exclamationmark.triangle")
                } actions: {
                    Button("try again") { Task { await model.load() } }
                }
            } else if let model, model.loaded {
                VStack(spacing: 8) {
                    HStack {
                        Spacer()
                        Button(CreateRoleCopy.button) { addingRole = true }
                    }
                    .padding(.horizontal)
                    if let toast = model.toast {
                        Text(toast).font(.footnote)
                    }
                    if model.deleteForbidden {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(model.deleteExplanationTitle).font(.headline)
                            Text(model.deleteExplanationBody).foregroundStyle(.secondary)
                        }
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding(.horizontal)
                    }
                    if let deleteError = model.deleteError {
                        Text(deleteError).font(.footnote).foregroundStyle(.red)
                    }
                    if model.roles.isEmpty {
                        ContentUnavailableView(AdminRolesCopy.empty, systemImage: "person.2")
                    } else {
                        List(model.roles) { role in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(adminRoleName(role))
                                    Text(adminRoleSubtitle(role))
                                        .font(.footnote)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Button(roleRowAction(role)) { editingRole = role }
                                if showsRoleDelete(role) {
                                    Button(RoleDeleteCopy.button, role: .destructive) {
                                        _ = model.prepareDelete(role)
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                ProgressView(AdminRolesCopy.loading)
            }
        }
        .sheet(isPresented: $addingRole) {
            NavigationStack {
                CreateRoleView(client: client) {
                    Task { await model?.load() }
                }
            }
        }
        .sheet(item: $editingRole) { role in
            NavigationStack {
                CreateRoleView(client: client, role: role) {
                    Task { await model?.load() }
                }
            }
        }
        .confirmationDialog(
            RoleDeleteCopy.title,
            isPresented: Binding(
                get: { model?.pendingDelete != nil },
                set: { if !$0 { model?.cancelDelete() } }
            ),
            titleVisibility: .visible
        ) {
            Button(RoleDeleteCopy.confirm, role: .destructive) {
                guard let role = model?.pendingDelete else { return }
                Task { _ = await model?.commitDelete(role) }
            }
            Button(RoleDeleteCopy.cancel, role: .cancel) {
                model?.cancelDelete()
            }
        } message: {
            if let role = model?.pendingDelete {
                Text(roleDeleteMessage(role))
            }
        }
        .task {
            if model == nil { model = AdminRolesModel(client: client) }
            await model?.load()
        }
    }
}
