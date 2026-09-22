import SwiftUI

enum GuidelinesCopy {
    static let title = "community guidelines"
    static let loading = "loading…"
    static let error = "couldn't load the guidelines — try refreshing"
}

func guidelinesURL(base: URL) -> URL {
    URL(string: "/api/community/guidelines/", relativeTo: base)!.absoluteURL
}

struct GuidelinesView: View {
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
                        PDAButton("try again") { Task { await load() } }
                    }
                } else {
                    ProgressView(GuidelinesCopy.loading)
                }
            }
            .navigationTitle(GuidelinesCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton("close", variant: .secondary) { dismiss() }
                }
            }
            .task { await load() }
        }
    }

    private func load() async {
        error = nil
        do {
            html = try await client.guidelines().contentHtml
        } catch {
            html = nil
            self.error = GuidelinesCopy.error
        }
    }
}
