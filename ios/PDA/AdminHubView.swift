import SwiftUI

enum AdminHubCopy {
    static let title = "admin"
}

struct AdminHubTile: Equatable, Identifiable {
    let id: String
    let label: String
    let detail: String
    let permission: String
}

private let adminHubCatalog: [AdminHubTile] = [
    AdminHubTile(id: "members", label: "members", detail: "create, edit, pause, or reset accounts", permission: "manage_users"),
    AdminHubTile(id: "join-requests", label: "join requests", detail: "approve or reject incoming applications", permission: "approve_join_requests"),
    AdminHubTile(id: "events", label: "events", detail: "review drafts, past, and cancelled events", permission: "manage_events"),
    AdminHubTile(id: "flagged-events", label: "flagged events", detail: "review and action flags from members", permission: "manage_events"),
    AdminHubTile(id: "attendance", label: "attendance", detail: "who came to events and when", permission: "manage_events"),
    AdminHubTile(id: "join-form", label: "join form", detail: "edit the questions asked on /join", permission: "edit_join_questions"),
    AdminHubTile(id: "docs", label: "docs", detail: "manage the shared document library", permission: "manage_documents"),
]

private let adminHubPermissions = [
    "manage_events",
    "manage_users",
    "approve_join_requests",
    "edit_join_questions",
    "manage_documents",
]

func hasAnyAdminPermission(_ user: SessionUser?) -> Bool {
    guard let user else { return false }
    if user.isAdmin { return true }
    return adminHubPermissions.contains { user.permissions.contains($0) }
}

func adminHubTiles(for user: SessionUser?) -> [AdminHubTile] {
    guard let user, hasAnyAdminPermission(user) else { return [] }
    return adminHubCatalog.filter { user.isAdmin || user.permissions.contains($0.permission) }
}

struct AdminHubView: View {
    let user: SessionUser?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List(adminHubTiles(for: user)) { tile in
                VStack(alignment: .leading, spacing: 4) {
                    Text(tile.label)
                    Text(tile.detail).font(.footnote).foregroundStyle(.secondary)
                }
            }
            .navigationTitle(AdminHubCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
        }
    }
}
