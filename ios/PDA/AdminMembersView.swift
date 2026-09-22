import SwiftUI

enum AdminMembersCopy {
    static let title = "members"
    static let loading = "loading…"
    static let error = "couldn't load members — try refreshing"
    static let empty = "no members yet 🌿"
    static let forbiddenTitle = "members"
    static let forbiddenBody = "you need permission to manage users to see this list."
    static let fallbackName = "member"
}

enum AdminMembersError: Error, Equatable {
    case forbidden
    case notFound
}

struct AdminMemberRole: Decodable, Equatable {
    let id: String
    let name: String
    let isDefault: Bool

    enum CodingKeys: String, CodingKey {
        case id, name
        case isDefault = "is_default"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decodeIfPresent(String.self, forKey: .id) ?? ""
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        isDefault = try c.decodeIfPresent(Bool.self, forKey: .isDefault) ?? false
    }
}

struct AdminMember: Decodable, Equatable, Identifiable {
    let id: String
    let fullName: String
    let phoneNumber: String
    let email: String
    let bio: String
    let firstName: String
    let lastName: String
    let isPaused: Bool
    let hasJoinedWhatsapp: Bool
    let roles: [AdminMemberRole]

    enum CodingKeys: String, CodingKey {
        case id
        case fullName = "full_name"
        case phoneNumber = "phone_number"
        case email
        case bio
        case firstName = "first_name"
        case lastName = "last_name"
        case isPaused = "is_paused"
        case hasJoinedWhatsapp = "has_joined_whatsapp"
        case roles
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        fullName = try c.decodeIfPresent(String.self, forKey: .fullName) ?? ""
        phoneNumber = try c.decodeIfPresent(String.self, forKey: .phoneNumber) ?? ""
        email = try c.decodeIfPresent(String.self, forKey: .email) ?? ""
        bio = try c.decodeIfPresent(String.self, forKey: .bio) ?? ""
        firstName = try c.decodeIfPresent(String.self, forKey: .firstName) ?? ""
        lastName = try c.decodeIfPresent(String.self, forKey: .lastName) ?? ""
        isPaused = try c.decodeIfPresent(Bool.self, forKey: .isPaused) ?? false
        hasJoinedWhatsapp = try c.decodeIfPresent(Bool.self, forKey: .hasJoinedWhatsapp) ?? false
        roles = try c.decodeIfPresent([AdminMemberRole].self, forKey: .roles) ?? []
    }
}

func adminMembersURL(base: URL) -> URL {
    URL(string: "/api/auth/users/", relativeTo: base)!.absoluteURL
}

func adminMemberSubtitle(_ member: AdminMember) -> String {
    member.phoneNumber.isEmpty ? member.email : member.phoneNumber
}

extension EventsClient {
    func adminMembers() async throws -> [AdminMember] {
        var req = URLRequest(url: adminMembersURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw AdminMembersError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([AdminMember].self, from: data)
    }
}

@Observable
final class AdminMembersModel {
    var client: EventsClient
    var members: [AdminMember] = []
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { AdminMembersCopy.forbiddenTitle }
    var explanationBody: String { AdminMembersCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            members = try await client.adminMembers()
            loaded = true
        } catch AdminMembersError.forbidden {
            members = []
            forbidden = true
            loaded = true
        } catch {
            members = []
            self.error = AdminMembersCopy.error
            loaded = true
        }
    }
}

struct AdminMembersView: View {
    var client: EventsClient
    var showRoles = false
    var canPauseAccounts = false
    var viewerIsAdmin = false
    @State private var tab = "members"
    @State private var model: AdminMembersModel?
    @State private var addingMember = false
    @State private var addingBulk = false

    var body: some View {
        VStack(spacing: 8) {
            if showRoles {
                Picker("tab", selection: $tab) {
                    ForEach(adminMembersTabs(showRoles: true), id: \.self) { name in
                        Text(name).tag(name)
                    }
                }
                .pickerStyle(.segmented)
                .padding(.horizontal)
            }
            if showRoles, tab == "roles" {
                AdminRolesView(client: client)
            } else {
                membersBody
            }
        }
        .navigationTitle(AdminMembersCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $addingMember) {
            NavigationStack {
                MemberCreateView(client: client)
            }
        }
        .sheet(isPresented: $addingBulk, onDismiss: { Task { await model?.load() } }) {
            NavigationStack {
                BulkCreateView(client: client)
            }
        }
        .task {
            if model == nil { model = AdminMembersModel(client: client) }
            await model?.load()
        }
    }

    private var membersBody: some View {
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
                    PDAButton("try again") { Task { await model.load() } }
                }
            } else if let model, model.loaded {
                VStack(spacing: 8) {
                    if showsAddMemberButton(tab: tab) {
                        HStack {
                            Spacer()
                            PDAButton(BulkCreateCopy.button, variant: .secondary) { addingBulk = true }
                            PDAButton(MemberCreateCopy.button) { addingMember = true }
                        }
                        .padding(.horizontal)
                    }
                    if model.members.isEmpty {
                        ContentUnavailableView(AdminMembersCopy.empty, systemImage: "person.2")
                    } else {
                        List(model.members) { member in
                            NavigationLink {
                                AdminMemberDetailView(
                                    userId: member.id,
                                    client: client,
                                    canManageUsers: canPauseAccounts,
                                    viewerIsAdmin: viewerIsAdmin
                                )
                            } label: {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text((member.fullName.isEmpty ? AdminMembersCopy.fallbackName : member.fullName).lowercased())
                                    let subtitle = adminMemberSubtitle(member)
                                    if !subtitle.isEmpty {
                                        Text(subtitle.lowercased()).font(.footnote).foregroundStyle(.secondary)
                                    }
                                }
                            }
                        }
                    }
                }
            } else {
                ProgressView(AdminMembersCopy.loading)
            }
        }
    }
}
