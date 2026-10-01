import SwiftUI

enum NotificationDestination: Hashable {
    case event(String)
    case checkIn(String)
    case joinRequests
    case flagged
    case member(String)
    case members

    var title: String {
        switch self {
        case .event: "event"
        case .checkIn: CheckInCopy.title
        case .joinRequests: "join requests"
        case .flagged: "flagged events"
        case .member, .members: "members"
        }
    }
}

func notificationTarget(_ n: AppNotification) -> NotificationDestination? {
    switch n.notificationType {
    case "event_invite", "cohost_added", "cohost_invite", "cohost_invite_accepted",
         "cohost_invite_declined", "cohost_removed", "waitlist_promoted", "event_cancelled",
         "comment_reply", "event_comment", "comment_reaction", "rsvp_declined_note",
         "rsvp_status_changed", "payment_revoked":
        return n.eventId.map(NotificationDestination.event)
    case "checkin_nudge":
        return n.eventId.map(NotificationDestination.checkIn)
    case "event_flagged":
        return .flagged
    case "join_request":
        return .joinRequests
    case "magic_link_request":
        return n.relatedUserId.map(NotificationDestination.member) ?? .members
    default:
        return nil
    }
}

struct NotificationsButton: View {
    @Environment(AuthSession.self) private var session
    @State private var unread = 0
    @State private var show = false

    var body: some View {
        Button {
            show = true
        } label: {
            ZStack(alignment: .topTrailing) {
                Image(systemName: "bell")
                if unread > 0 {
                    Text(unread > 99 ? "99+" : "\(unread)")
                        .font(.caption2.weight(.medium))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 4)
                        .background(.red, in: Capsule())
                        .offset(x: 8, y: -8)
                }
            }
        }
        .accessibilityLabel(NotificationsCopy.bellLabel(unread: unread))
        .sheet(isPresented: $show) {
            NotificationsView()
                .environment(session)
        }
        .task { await pollUnread() }
    }

    private func pollUnread() async {
        while !Task.isCancelled {
            unread = (try? await session.client.unreadNotificationCount()) ?? unread
            try? await Task.sleep(nanoseconds: NotificationsCopy.pollNanoseconds)
        }
    }
}

struct NotificationsView: View {
    @Environment(AuthSession.self) private var session
    @Environment(\.dismiss) private var dismiss
    @State private var rows: [AppNotification] = []
    @State private var error: String?
    @State private var loading = true
    @State private var loadingMore = false
    @State private var hasMore = false
    @State private var target: NotificationDestination?

    var body: some View {
        NavigationStack {
            Group {
                if loading && rows.isEmpty {
                    ProgressView(NotificationsCopy.title)
                } else if rows.isEmpty, error != nil {
                    ContentUnavailableView {
                        Label(NotificationsCopy.error, systemImage: "exclamationmark.triangle")
                    } actions: {
                        PDAButton("try again") { Task { await load(reset: true) } }
                    }
                } else if rows.isEmpty {
                    ContentUnavailableView(NotificationsCopy.empty, systemImage: "leaf")
                } else {
                    List {
                        ForEach(rows) { n in
                            Button {
                                Task { await open(n) }
                            } label: {
                                HStack(alignment: .top, spacing: 8) {
                                    Circle()
                                        .frame(width: 8, height: 8)
                                        .padding(.top, 6)
                                        .opacity(n.isRead ? 0 : 1)
                                    Text(n.message)
                                        .foregroundStyle(.primary)
                                        .multilineTextAlignment(.leading)
                                }
                            }
                        }
                        if hasMore {
                            PDAButton(NotificationsCopy.loadMore, variant: .secondary) {
                                Task { await load(reset: false) }
                            }
                            .disabled(loadingMore)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationTitle(NotificationsCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton("close", variant: .secondary) { dismiss() }
                }
            }
            .navigationDestination(item: $target) { dest in
                NotificationTargetView(destination: dest)
            }
            .task { await poll() }
        }
    }

    private func poll() async {
        while !Task.isCancelled {
            await load(reset: true)
            try? await Task.sleep(nanoseconds: NotificationsCopy.pollNanoseconds)
        }
    }

    private func load(reset: Bool) async {
        if reset {
            loading = rows.isEmpty
        } else {
            loadingMore = true
        }
        defer {
            loading = false
            loadingMore = false
        }
        do {
            let page = try await session.client.listNotifications(offset: reset ? 0 : rows.count)
            rows = reset ? page : rows + page
            hasMore = page.count == NotificationsCopy.pageSize
            error = nil
        } catch {
            self.error = NotificationsCopy.error
        }
    }

    private func open(_ n: AppNotification) async {
        await markRead(n)
        target = notificationTarget(n)
    }

    private func markRead(_ n: AppNotification) async {
        guard !n.isRead else { return }
        do {
            try await session.client.markNotificationRead(n.id)
            if let i = rows.firstIndex(where: { $0.id == n.id }) {
                rows[i] = AppNotification(
                    id: n.id,
                    notificationType: n.notificationType,
                    eventId: n.eventId,
                    relatedUserId: n.relatedUserId,
                    message: n.message,
                    isRead: true,
                    createdAt: n.createdAt
                )
            }
        } catch {
            self.error = NotificationsCopy.error
        }
    }
}

private struct NotificationTargetView: View {
    let destination: NotificationDestination
    @Environment(AuthSession.self) private var session
    @State private var event: Event?
    @State private var error: String?

    var body: some View {
        switch destination {
        case .event, .checkIn:
            if let event {
                if case .checkIn = destination {
                    CheckInView(event: event, client: eventsClient, onUpdated: { _ in })
                } else {
                    EventDetailView(event: event)
                }
            } else if let error {
                ContentUnavailableView(error, systemImage: "exclamationmark.triangle")
            } else {
                ProgressView().task { await loadEvent() }
            }
        case .joinRequests, .flagged, .members:
            ContentUnavailableView(destination.title, systemImage: "leaf")
        case let .member(id):
            ProfileView(userId: id, client: eventsClient)
        }
    }

    private var eventsClient: EventsClient {
        EventsClient(tokens: session.client.tokens)
    }

    private func loadEvent() async {
        guard let id else { return }
        do {
            event = try await eventsClient.event(id: id)
        } catch {
            self.error = NotificationsCopy.error
        }
    }

    private var id: String? {
        switch destination {
        case let .event(id), let .checkIn(id): id
        default: nil
        }
    }
}
