import SwiftUI

struct NotificationsButton: View {
    @Environment(AuthSession.self) private var session
    @State private var unread = 0
    @State private var show = false

    var body: some View {
        Button(unread > 0 ? "\(NotificationsCopy.title) (\(unread) unread)" : NotificationsCopy.title) {
            show = true
        }
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

    var body: some View {
        NavigationStack {
            Group {
                if loading && rows.isEmpty {
                    ProgressView(NotificationsCopy.title)
                } else if rows.isEmpty, error != nil {
                    ContentUnavailableView {
                        Label(NotificationsCopy.error, systemImage: "exclamationmark.triangle")
                    } actions: {
                        Button("try again") { Task { await load(reset: true) } }
                    }
                } else if rows.isEmpty {
                    ContentUnavailableView(NotificationsCopy.empty, systemImage: "leaf")
                } else {
                    List {
                        ForEach(rows) { n in
                            Button {
                                Task { await markRead(n) }
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
                            Button(NotificationsCopy.loadMore) {
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
                    Button("close") { dismiss() }
                }
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
