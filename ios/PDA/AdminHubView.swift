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

enum AdminHubDestination: Equatable {
    case members
    case joinRequests
    case events
    case flaggedEvents
    case attendance
    case docs
    case joinForm
}

func adminHubDestination(for tile: AdminHubTile) -> AdminHubDestination? {
    switch tile.id {
    case "members": .members
    case "join-requests": .joinRequests
    case "events": .events
    case "flagged-events": .flaggedEvents
    case "attendance": .attendance
    case "docs": .docs
    case "join-form": .joinForm
    default: nil
    }
}

struct AdminHubView: View {
    let user: SessionUser?
    var client = EventsClient()
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            List(adminHubTiles(for: user)) { tile in
                if let destination = adminHubDestination(for: tile) {
                    NavigationLink {
                        hubDestination(destination)
                    } label: {
                        hubTileLabel(tile)
                    }
                } else {
                    hubTileLabel(tile)
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

    @ViewBuilder
    private func hubDestination(_ destination: AdminHubDestination) -> some View {
        switch destination {
        case .members:
            AdminMembersView(
                client: client,
                showRoles: showsAdminRolesTab(user),
                canPauseAccounts: showsPauseAccount(user)
            )
        case .joinRequests:
            JoinRequestsView(client: client)
        case .events:
            ManageEventsView(client: client)
        case .flaggedEvents:
            FlaggedEventsView(client: client)
        case .attendance:
            AttendanceReportView(client: client)
        case .docs:
            DocsLibraryView(client: client)
        case .joinForm:
            AdminJoinFormView(client: client)
        }
    }

    private func hubTileLabel(_ tile: AdminHubTile) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(tile.label)
            Text(tile.detail).font(.footnote).foregroundStyle(.secondary)
        }
    }
}
