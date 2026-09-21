import SwiftUI

enum VolunteerCopy {
    static let title = "volunteer"
    static let loading = "loading…"
    static let error = "couldn't load the volunteer page — try refreshing"
}

func volunteerURL(base: URL) -> URL {
    URL(string: "/api/community/pages/volunteer/", relativeTo: base)!.absoluteURL
}

func canShowVolunteer(user: SessionUser?) -> Bool {
    user != nil
}

struct VolunteerView: View {
    var client = EventsClient()
    @Environment(\.dismiss) private var dismiss
    @State private var html: String?
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Group {
                if let html {
                    ContentHTMLView(html: html, baseURL: client.baseURL)
                } else if let error {
                    ContentUnavailableView {
                        Label(error, systemImage: "exclamationmark.triangle")
                    } actions: {
                        Button("try again") { Task { await load() } }
                    }
                } else {
                    ProgressView(VolunteerCopy.loading)
                }
            }
            .navigationTitle(VolunteerCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
            .task { await load() }
        }
    }

    private func load() async {
        error = nil
        do {
            html = try await client.volunteer().contentHtml
        } catch {
            html = nil
            self.error = VolunteerCopy.error
        }
    }
}
