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

    enum CodingKeys: String, CodingKey {
        case id, name, permissions
        case userCount = "user_count"
    }

    init(id: String, name: String, permissions: [String], userCount: Int) {
        self.id = id
        self.name = name
        self.permissions = permissions
        self.userCount = userCount
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        permissions = try c.decodeIfPresent([String].self, forKey: .permissions) ?? []
        userCount = try c.decodeIfPresent(Int.self, forKey: .userCount) ?? 0
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
}

@Observable
final class AdminRolesModel {
    var client: EventsClient
    var roles: [AdminRole] = []
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { AdminRolesCopy.forbiddenTitle }
    var explanationBody: String { AdminRolesCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
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
                    if model.roles.isEmpty {
                        ContentUnavailableView(AdminRolesCopy.empty, systemImage: "person.2")
                    } else {
                        List(model.roles) { role in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(adminRoleName(role))
                                Text(adminRoleSubtitle(role))
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
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
        .task {
            if model == nil { model = AdminRolesModel(client: client) }
            await model?.load()
        }
    }
}
