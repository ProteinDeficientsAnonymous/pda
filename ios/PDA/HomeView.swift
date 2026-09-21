import SwiftUI
import WebKit

enum HomeCopy {
    static let title = "home"
    static let loading = "loading…"
    static let error = "couldn't load the home page — try refreshing"
}

struct HomePage: Decodable, Equatable {
    var content: String
    var contentPm: String
    var contentHtml: String
    var updatedAt: String

    enum CodingKeys: String, CodingKey {
        case content
        case contentPm = "content_pm"
        case contentHtml = "content_html"
        case updatedAt = "updated_at"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        content = try c.decodeIfPresent(String.self, forKey: .content) ?? ""
        contentPm = try c.decodeIfPresent(String.self, forKey: .contentPm) ?? ""
        contentHtml = try c.decodeIfPresent(String.self, forKey: .contentHtml) ?? ""
        updatedAt = try c.decode(String.self, forKey: .updatedAt)
    }
}

func homeURL(base: URL) -> URL {
    URL(string: "/api/community/home/", relativeTo: base)!.absoluteURL
}

struct HomeView: View {
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
                    ProgressView(HomeCopy.loading)
                }
            }
            .navigationTitle(HomeCopy.title)
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
            html = try await client.home().contentHtml
        } catch {
            html = nil
            self.error = HomeCopy.error
        }
    }
}

struct ContentHTMLView: UIViewRepresentable {
    let html: String
    let baseURL: URL

    func makeUIView(context: Context) -> WKWebView {
        let view = WKWebView(frame: .zero)
        view.isOpaque = false
        view.backgroundColor = .clear
        return view
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        webView.loadHTMLString(
            """
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>body{font-family:-apple-system;margin:0;padding:16px;color:CanvasText;background:transparent}</style>
            \(html)
            """,
            baseURL: baseURL
        )
    }
}
