import SwiftUI

enum DonateCopy {
    static let title = "donate"
    static let loading = "loading…"
    static let error = "couldn't load the donate page — try refreshing"
}

func donateURL(base: URL) -> URL {
    URL(string: "/api/community/pages/donate/", relativeTo: base)!.absoluteURL
}

struct DonateView: View {
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
                    ProgressView(DonateCopy.loading)
                }
            }
            .navigationTitle(DonateCopy.title)
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
            html = try await client.donate().contentHtml
        } catch {
            html = nil
            self.error = DonateCopy.error
        }
    }
}
