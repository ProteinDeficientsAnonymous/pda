import SwiftUI

enum DocsLibraryCopy {
    static let title = "docs"
    static let loading = "loading…"
    static let error = "couldn't load the docs — try refreshing"
    static let empty = "nothing here yet 🌿"
    static let forbiddenTitle = "docs"
    static let forbiddenBody = "you need permission to manage documents to see this list."
}

enum DocsLibraryError: Error, Equatable {
    case forbidden
}

struct DocSummary: Decodable, Equatable, Identifiable {
    let id: String
    let title: String

    init(id: String, title: String) {
        self.id = id
        self.title = title
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
    }

    private enum CodingKeys: String, CodingKey {
        case id, title
    }
}

struct DocFolder: Decodable, Equatable, Identifiable {
    let id: String
    let name: String
    let documents: [DocSummary]
    let children: [DocFolder]

    init(id: String, name: String, documents: [DocSummary], children: [DocFolder]) {
        self.id = id
        self.name = name
        self.documents = documents
        self.children = children
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        name = try c.decodeIfPresent(String.self, forKey: .name) ?? ""
        documents = try c.decodeIfPresent([DocSummary].self, forKey: .documents) ?? []
        children = try c.decodeIfPresent([DocFolder].self, forKey: .children) ?? []
    }

    private enum CodingKeys: String, CodingKey {
        case id, name, documents, children
    }
}

func docsLibraryURL(base: URL) -> URL {
    URL(string: "/api/community/docs/folders/", relativeTo: base)!.absoluteURL
}

func docsLibraryLines(_ folders: [DocFolder]) -> [String] {
    folders.flatMap(docsFolderLines)
}

private func docsFolderLines(_ folder: DocFolder) -> [String] {
    [folder.name.lowercased()]
        + folder.documents.map { $0.title.lowercased() }
        + folder.children.flatMap(docsFolderLines)
}

extension EventsClient {
    func docsLibrary() async throws -> [DocFolder] {
        var req = URLRequest(url: docsLibraryURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw DocsLibraryError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([DocFolder].self, from: data)
    }
}

@Observable
final class DocsLibraryModel {
    var client: EventsClient
    var folders: [DocFolder] = []
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { DocsLibraryCopy.forbiddenTitle }
    var explanationBody: String { DocsLibraryCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            folders = try await client.docsLibrary()
            loaded = true
        } catch DocsLibraryError.forbidden {
            folders = []
            forbidden = true
            loaded = true
        } catch {
            folders = []
            self.error = DocsLibraryCopy.error
            loaded = true
        }
    }
}

struct DocsLibraryView: View {
    var client: EventsClient
    @State private var model: DocsLibraryModel?

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
                    Button("try again") { Task { await model.load() } }
                }
            } else if let model, model.loaded {
                if model.folders.isEmpty {
                    ContentUnavailableView(DocsLibraryCopy.empty, systemImage: "doc")
                } else {
                    List {
                        ForEach(model.folders) { folder in
                            DocsFolderBlock(folder: folder)
                        }
                    }
                }
            } else {
                ProgressView(DocsLibraryCopy.loading)
            }
        }
        .navigationTitle(DocsLibraryCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = DocsLibraryModel(client: client) }
            await model?.load()
        }
    }
}

private struct DocsFolderBlock: View {
    let folder: DocFolder

    var body: some View {
        Section {
            ForEach(folder.documents) { doc in
                Text(doc.title.lowercased())
            }
            ForEach(folder.children) { child in
                DocsFolderBlock(folder: child)
            }
        } header: {
            Text(folder.name.lowercased())
        }
    }
}
