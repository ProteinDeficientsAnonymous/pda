import SwiftUI

enum DirectoryCopy {
    static let title = "members"
    static let search = "search name, email, or phone"
    static let loading = "loading…"
    static let error = "couldn't load members — try refreshing"
    static let empty = "no members yet 🌿"
    static let profileError = "couldn't load this profile — try again"
    static let contactHidden = "contact info hidden"
    static let bio = "bio"
    static let fallbackName = "member"
}

enum DirectoryError: Error, Equatable {
    case forbidden
}

struct DirectoryMember: Decodable, Equatable, Identifiable, Hashable {
    let id: String
    let fullName: String
    let phoneNumber: String
    let email: String
    let profilePhotoUrl: String

    enum CodingKeys: String, CodingKey {
        case id
        case fullName = "full_name"
        case phoneNumber = "phone_number"
        case email
        case profilePhotoUrl = "profile_photo_url"
    }

    init(id: String, fullName: String, phoneNumber: String, email: String, profilePhotoUrl: String) {
        self.id = id
        self.fullName = fullName
        self.phoneNumber = phoneNumber
        self.email = email
        self.profilePhotoUrl = profilePhotoUrl
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        fullName = try c.decodeIfPresent(String.self, forKey: .fullName) ?? ""
        phoneNumber = try c.decodeIfPresent(String.self, forKey: .phoneNumber) ?? ""
        email = try c.decodeIfPresent(String.self, forKey: .email) ?? ""
        profilePhotoUrl = try c.decodeIfPresent(String.self, forKey: .profilePhotoUrl) ?? ""
    }
}

func directoryURL(base: URL) -> URL {
    URL(string: "/api/auth/users/directory/", relativeTo: base)!.absoluteURL
}

func directorySubtitle(phone: String, email: String) -> String {
    phone.isEmpty ? email : phone
}

func directoryInitials(_ name: String) -> String {
    let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
    guard !trimmed.isEmpty else { return "?" }
    return String(trimmed.prefix(2)).lowercased()
}

func filterDirectory(_ members: [DirectoryMember], query: String) -> [DirectoryMember] {
    let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    guard !q.isEmpty else { return members }
    return members.filter {
        $0.fullName.lowercased().contains(q)
            || $0.phoneNumber.lowercased().contains(q)
            || $0.email.lowercased().contains(q)
    }
}

func directoryEmptyMessage(total: Int, query: String) -> String {
    total == 0 ? DirectoryCopy.empty : "no one matches \"\(query)\" 🌿"
}

func profileDisplayName(_ profile: MemberProfile) -> String {
    profile.name.isEmpty ? DirectoryCopy.fallbackName : profile.name
}

func profileContactLines(_ profile: MemberProfile) -> [String] {
    let lines = [profile.phoneNumber, profile.email].filter { !$0.isEmpty }
    return lines.isEmpty ? [DirectoryCopy.contactHidden] : lines
}

extension EventsClient {
    func directory() async throws -> [DirectoryMember] {
        var req = URLRequest(url: directoryURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw DirectoryError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([DirectoryMember].self, from: data)
    }

    func memberProfile(id: String) async throws -> MemberProfile {
        do {
            return try await profile(userId: id)
        } catch APIError.http(let status) where status == 403 {
            throw DirectoryError.forbidden
        }
    }
}

@Observable
final class DirectoryModel {
    var client: EventsClient
    var members: [DirectoryMember] = []
    var query = ""
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { MemberLockCopy.directoryTitle }
    var explanationBody: String { MemberLockCopy.directoryBody }
    var visible: [DirectoryMember] { filterDirectory(members, query: query) }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            members = try await client.directory()
            loaded = true
        } catch DirectoryError.forbidden {
            members = []
            forbidden = true
            loaded = true
        } catch {
            members = []
            self.error = DirectoryCopy.error
            loaded = true
        }
    }
}

struct DirectoryView: View {
    var client: EventsClient
    @State private var model: DirectoryModel?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
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
                    List {
                        if model.visible.isEmpty {
                            Text(directoryEmptyMessage(total: model.members.count, query: model.query))
                                .foregroundStyle(.secondary)
                        } else {
                            ForEach(model.visible) { member in
                                NavigationLink(value: member) {
                                    VStack(alignment: .leading, spacing: 2) {
                                        Text((member.fullName.isEmpty ? DirectoryCopy.fallbackName : member.fullName).lowercased())
                                        let subtitle = directorySubtitle(phone: member.phoneNumber, email: member.email)
                                        if !subtitle.isEmpty {
                                            Text(subtitle.lowercased()).font(.footnote).foregroundStyle(.secondary)
                                        }
                                    }
                                }
                            }
                        }
                    }
                    .searchable(text: Bindable(model).query, prompt: DirectoryCopy.search)
                } else {
                    ProgressView(DirectoryCopy.loading)
                }
            }
            .navigationTitle(DirectoryCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton("close", variant: .secondary) { dismiss() }
                }
            }
            .navigationDestination(for: DirectoryMember.self) { member in
                DirectoryProfileView(userId: member.id, client: client)
            }
            .task {
                if model == nil { model = DirectoryModel(client: client) }
                await model?.load()
            }
        }
    }
}

struct DirectoryProfileView: View {
    let userId: String
    var client: EventsClient
    @State private var profile: MemberProfile?
    @State private var forbidden = false
    @State private var error: String?

    var body: some View {
        Group {
            if forbidden {
                VStack(alignment: .leading, spacing: 12) {
                    Text(MemberLockCopy.directoryTitle).font(.title2)
                    Text(MemberLockCopy.directoryBody).foregroundStyle(.secondary)
                    Spacer()
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
            } else if let profile {
                List {
                    Text(profileDisplayName(profile).lowercased()).font(.headline)
                    if !profile.nickname.isEmpty {
                        Text("\"\(profile.nickname.lowercased())\"").foregroundStyle(.secondary)
                    }
                    if !profile.pronouns.isEmpty {
                        Text(profile.pronouns.lowercased()).foregroundStyle(.secondary)
                    }
                    if let birthday = profile.birthday {
                        Text(formatBirthday(birthday))
                    }
                    ForEach(profileContactLines(profile), id: \.self) { line in
                        Text(line.lowercased())
                    }
                    if !profile.bio.isEmpty {
                        Section(DirectoryCopy.bio) {
                            Text(profile.bio.lowercased())
                        }
                    }
                }
            } else if let error {
                ContentUnavailableView {
                    Label(error, systemImage: "exclamationmark.triangle")
                } actions: {
                    PDAButton("try again") { Task { await load() } }
                }
            } else {
                ProgressView(DirectoryCopy.loading)
            }
        }
        .navigationTitle(DirectoryCopy.fallbackName)
        .navigationBarTitleDisplayMode(.inline)
        .task { await load() }
    }

    private func load() async {
        error = nil
        forbidden = false
        do {
            profile = try await client.memberProfile(id: userId)
        } catch DirectoryError.forbidden {
            profile = nil
            forbidden = true
        } catch {
            profile = nil
            self.error = DirectoryCopy.profileError
        }
    }
}
