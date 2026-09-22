import SwiftUI

enum CreateRoleCopy {
    static let button = "add role"
    static let title = "create role"
    static let name = "name"
    static let placeholder = "e.g. greeter"
    static let permissions = "permissions"
    static let cancel = "cancel"
    static let create = "create"
    static let saving = "saving…"
    static let nameRequired = "role name is required"
    static let failure = "something went wrong — try again"
    static let forbiddenTitle = "create role"
    static let forbiddenBody = "you need permission to manage roles to create a role."
    static let edit = "edit"
    static let view = "view"
    static let editTitle = "edit role"
    static let viewTitle = "view role"
    static let save = "save"
    static let close = "close"
    static let builtIn = "built-in role — view only"
    static let editForbiddenBody = "you need permission to manage roles to edit this role."
}

enum CreateRoleError: Error, Equatable {
    case forbidden
}

struct RolePermissionChoice: Equatable {
    let key: String
    let label: String
}

let roleNameMaxLength = 40

let rolePermissionChoices: [RolePermissionChoice] = [
    RolePermissionChoice(key: "create_user", label: "create users"),
    RolePermissionChoice(key: "manage_users", label: "manage users"),
    RolePermissionChoice(key: "manage_roles", label: "manage roles"),
    RolePermissionChoice(key: "approve_join_requests", label: "approve join requests"),
    RolePermissionChoice(key: "manage_events", label: "manage events"),
    RolePermissionChoice(key: "edit_guidelines", label: "edit guidelines"),
    RolePermissionChoice(key: "edit_faq", label: "edit faq"),
    RolePermissionChoice(key: "edit_homepage", label: "edit homepage"),
    RolePermissionChoice(key: "edit_join_questions", label: "edit join questions"),
    RolePermissionChoice(key: "manage_surveys", label: "manage surveys"),
    RolePermissionChoice(key: "tag_official_event", label: "tag official events"),
    RolePermissionChoice(key: "tag_club_event", label: "tag club events"),
    RolePermissionChoice(key: "manage_documents", label: "manage documents"),
    RolePermissionChoice(key: "manage_feature_flags", label: "manage feature flags"),
]

func clampedRoleName(_ name: String) -> String {
    String(name.prefix(roleNameMaxLength))
}

func updateRoleURL(base: URL, id: String) -> URL {
    URL(string: "/api/auth/roles/\(id)/", relativeTo: base)!.absoluteURL
}

func roleRowAction(_ role: AdminRole) -> String {
    role.isDefault ? CreateRoleCopy.view : CreateRoleCopy.edit
}

extension EventsClient {
    func createRole(name: String, permissions: [String]) async throws -> AdminRole {
        var req = URLRequest(url: adminRolesURL(base: baseURL))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "name": name,
            "permissions": permissions,
        ])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw CreateRoleError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(AdminRole.self, from: data)
    }

    func updateRole(id: String, name: String, permissions: [String]) async throws -> AdminRole {
        var req = URLRequest(url: updateRoleURL(base: baseURL, id: id))
        req.httpMethod = "PATCH"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "name": name,
            "permissions": permissions,
        ])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw CreateRoleError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(AdminRole.self, from: data)
    }
}

@Observable
final class CreateRoleModel {
    var client: EventsClient
    var role: AdminRole?
    var name = ""
    var permissions: [String] = []
    var formError: String?
    var forbidden = false
    var closed = false
    var saving = false
    var created: AdminRole?

    var readOnly: Bool { role?.isDefault == true }
    var canSave: Bool { !readOnly && !saving }
    var title: String {
        guard let role else { return CreateRoleCopy.title }
        return role.isDefault ? CreateRoleCopy.viewTitle : CreateRoleCopy.editTitle
    }
    var builtInNote: String { CreateRoleCopy.builtIn }
    var explanationTitle: String { role == nil ? CreateRoleCopy.forbiddenTitle : CreateRoleCopy.editTitle }
    var explanationBody: String { role == nil ? CreateRoleCopy.forbiddenBody : CreateRoleCopy.editForbiddenBody }

    init(client: EventsClient = EventsClient(), role: AdminRole? = nil) {
        self.client = client
        self.role = role
        if let role {
            name = role.name
            permissions = role.permissions
        }
    }

    func togglePermission(_ key: String) {
        if readOnly { return }
        if let index = permissions.firstIndex(of: key) {
            permissions.remove(at: index)
        } else {
            permissions.append(key)
        }
    }

    func submit() async -> Bool {
        if readOnly { return false }
        formError = nil
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            formError = CreateRoleCopy.nameRequired
            return false
        }
        saving = true
        defer { saving = false }
        let nextName = clampedRoleName(trimmed)
        do {
            if let role {
                created = try await client.updateRole(id: role.id, name: nextName, permissions: permissions)
            } else {
                created = try await client.createRole(name: nextName, permissions: permissions)
            }
            closed = true
            return true
        } catch CreateRoleError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = CreateRoleCopy.failure
            return false
        }
    }

    func cancel() {
        closed = true
    }
}

struct CreateRoleView: View {
    var client: EventsClient
    var role: AdminRole?
    var onCreated: () -> Void = {}
    @Environment(\.dismiss) private var dismiss
    @State private var model: CreateRoleModel?

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
            } else if let model {
                Form {
                    Section {
                        PDATextField(
                            CreateRoleCopy.placeholder,
                            text: nameBinding(model),
                            capitalization: .never,
                            disableAutocorrection: true
                        )
                        .disabled(model.readOnly)
                        if model.readOnly {
                            Text(model.builtInNote)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    } header: {
                        Text(CreateRoleCopy.name)
                    }
                    Section(CreateRoleCopy.permissions) {
                        ForEach(rolePermissionChoices, id: \.key) { choice in
                            Toggle(choice.label, isOn: permissionBinding(model, choice.key))
                                .disabled(model.readOnly)
                        }
                    }
                    if let formError = model.formError {
                        Text(formError).foregroundStyle(.red)
                    }
                }
            }
        }
        .navigationTitle(model?.title ?? CreateRoleCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                PDAButton(model?.readOnly == true ? CreateRoleCopy.close : CreateRoleCopy.cancel, variant: .secondary) {
                    model?.cancel()
                    dismiss()
                }
            }
            if model?.readOnly != true, model?.forbidden != true {
                ToolbarItem(placement: .confirmationAction) {
                    PDAButton(saveLabel) {
                        Task { await submit() }
                    }
                    .disabled(model?.saving == true)
                }
            }
        }
        .task {
            if model == nil { model = CreateRoleModel(client: client, role: role) }
        }
    }

    private var saveLabel: String {
        if model?.saving == true { return CreateRoleCopy.saving }
        return model?.role == nil ? CreateRoleCopy.create : CreateRoleCopy.save
    }

    private func nameBinding(_ model: CreateRoleModel) -> Binding<String> {
        Binding(get: { model.name }, set: { model.name = clampedRoleName($0) })
    }

    private func permissionBinding(_ model: CreateRoleModel, _ key: String) -> Binding<Bool> {
        Binding(
            get: { model.permissions.contains(key) },
            set: { _ in model.togglePermission(key) }
        )
    }

    private func submit() async {
        guard let model, await model.submit() else { return }
        onCreated()
        dismiss()
    }
}
