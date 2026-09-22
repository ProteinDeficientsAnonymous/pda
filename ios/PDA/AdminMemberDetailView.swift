import SwiftUI

enum AdminMemberDetailCopy {
    static let notFound = "member not found"
    static let error = "couldn't load members — try refreshing"
    static let bio = "bio"
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
}

@Observable
final class AdminMemberDetailModel {
    var client: EventsClient
    var member: AdminMember?
    var forbidden = false
    var error: String?

    var explanationTitle: String { AdminMembersCopy.forbiddenTitle }
    var explanationBody: String { AdminMembersCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load(id: String) async {
        error = nil
        forbidden = false
        member = nil
        do {
            member = try await client.adminMemberDetail(id: id)
        } catch AdminMembersError.forbidden {
            forbidden = true
        } catch AdminMembersError.notFound {
            error = AdminMemberDetailCopy.notFound
        } catch {
            self.error = AdminMemberDetailCopy.error
        }
    }
}

struct AdminMemberDetailView: View {
    let userId: String
    var client: EventsClient
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
            } else if let model, let member = model.member {
                List {
                    Text(adminMemberDetailTitle(member).lowercased()).font(.headline)
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
