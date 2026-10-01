import SwiftUI

enum DocDetailCopy {
    static let loading = "loading…"
    static let error = "couldn't load this doc — try refreshing"
    static let forbiddenTitle = "docs"
    static let forbiddenBody = "you need permission to manage documents to see this document."
}

enum DocDetailError: Error, Equatable {
    case forbidden
}

struct LibraryDocument: Decodable, Equatable, Identifiable {
    let id: String
    let title: String
    let contentHtml: String

    enum CodingKeys: String, CodingKey {
        case id, title
        case contentHtml = "content_html"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        contentHtml = try c.decodeIfPresent(String.self, forKey: .contentHtml) ?? ""
    }
}

func docDetailURL(base: URL, id: String) -> URL {
    URL(string: "/api/community/docs/\(id)/", relativeTo: base)!.absoluteURL
}

func docDetailTitle(_ doc: LibraryDocument) -> String {
    let title = doc.title.trimmingCharacters(in: .whitespacesAndNewlines)
    return title.isEmpty ? "doc" : title.lowercased()
}

extension EventsClient {
    func document(id: String) async throws -> LibraryDocument {
        var req = URLRequest(url: docDetailURL(base: baseURL, id: id))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw DocDetailError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(LibraryDocument.self, from: data)
    }
}

@Observable
final class DocDetailModel {
    var client: EventsClient
    let docId: String
    var document: LibraryDocument?
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { DocDetailCopy.forbiddenTitle }
    var explanationBody: String { DocDetailCopy.forbiddenBody }

    init(client: EventsClient, docId: String) {
        self.client = client
        self.docId = docId
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            document = try await client.document(id: docId)
            loaded = true
        } catch DocDetailError.forbidden {
            document = nil
            forbidden = true
            loaded = true
        } catch {
            document = nil
            self.error = DocDetailCopy.error
            loaded = true
        }
    }
}

struct DocDetailView: View {
    let docId: String
    var client: EventsClient
    @State private var model: DocDetailModel?

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
            } else if let model, let error = model.error {
                ContentUnavailableView {
                    Label(error, systemImage: "exclamationmark.triangle")
                } actions: {
                    PDAButton("try again") { Task { await model.load() } }
                }
            } else if let doc = model?.document {
                VStack(alignment: .leading, spacing: 12) {
                    Text(docDetailTitle(doc)).font(.title2)
                    ContentHTMLView(html: doc.contentHtml, baseURL: client.baseURL)
                }
                .padding()
                .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            } else {
                ProgressView(DocDetailCopy.loading)
            }
        }
        .navigationTitle(model?.document.map(docDetailTitle) ?? DocDetailCopy.forbiddenTitle)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = DocDetailModel(client: client, docId: docId) }
            await model?.load()
        }
    }
}
