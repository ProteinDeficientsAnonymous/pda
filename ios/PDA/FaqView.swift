import SwiftUI

enum FaqCopy {
    static let title = "faq"
    static let loading = "loading…"
    static let error = "couldn't load the faq — try refreshing"
}

func faqURL(base: URL) -> URL {
    URL(string: "/api/community/faq/", relativeTo: base)!.absoluteURL
}

struct FaqView: View {
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
                    ProgressView(FaqCopy.loading)
                }
            }
            .navigationTitle(FaqCopy.title)
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
            html = try await client.faq().contentHtml
        } catch {
            html = nil
            self.error = FaqCopy.error
        }
    }
}
