import SwiftUI

enum ImageSearchCopy {
    static let title = "choose an image"
    static let library = "library"
    static let upload = "upload your own"
    static let placeholder = "search gifs and photos"
    static let searching = "searching…"
    static let empty = "nothing found — try another search"
    static let searchError = "couldn't search images — try again"
    static let loadError = "couldn't load that image — try another"
    static let typeError = "pick a jpeg, png, webp, gif, or heic image"
    static let sizeError = "photo must be under 10 mb"
    static let drop = "tap or drop a photo"
    static let cancel = "cancel"
    static let attribution = "powered by giphy"
}

private let photoMimeTypes = [
    "image/jpeg", "image/png", "image/webp", "image/gif", "image/heic", "image/heif",
]
private let maxPhotoBytes = 10 * 1024 * 1024

struct ImageHit: Decodable, Equatable, Identifiable {
    var id: String
    var title: String
    var previewURL: String
    var originalURL: String
    var source: String

    enum CodingKeys: String, CodingKey {
        case id, title, source
        case previewURL = "preview_url"
        case originalURL = "original_url"
    }
}

func photoUploadError(mime: String, bytes: Int) -> String? {
    if !photoMimeTypes.contains(mime) { return ImageSearchCopy.typeError }
    if bytes > maxPhotoBytes { return ImageSearchCopy.sizeError }
    return nil
}

func giphySearchURL(base: URL, query: String) -> URL {
    var comps = URLComponents(
        url: URL(string: "/api/community/giphy/search/", relativeTo: base)!.absoluteURL,
        resolvingAgainstBaseURL: false
    )!
    let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
    var items = [URLQueryItem(name: "limit", value: "24")]
    if !trimmed.isEmpty {
        items.insert(URLQueryItem(name: "q", value: trimmed), at: 0)
    }
    comps.queryItems = items
    return comps.url!
}

extension EventsClient {
    func searchImages(_ query: String) async throws -> [ImageHit] {
        var req = URLRequest(url: giphySearchURL(base: baseURL, query: query))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        struct Out: Decodable { let results: [ImageHit] }
        return try Event.decoder.decode(Out.self, from: data).results
    }
}

@Observable
final class ImageSearchModel {
    var query = ""
    var results: [ImageHit] = []
    var error: String?
    var busy = false
    var client: EventsClient

    init(client: EventsClient) {
        self.client = client
    }

    var showsGiphyMark: Bool { results.contains { $0.source == "gif" } }

    var empty: String? {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        if error == nil, !busy, results.isEmpty, !trimmed.isEmpty {
            return ImageSearchCopy.empty
        }
        return nil
    }

    func search(_ raw: String) async {
        query = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        busy = true
        error = nil
        defer { busy = false }
        do {
            results = try await client.searchImages(query)
        } catch {
            results = []
            self.error = ImageSearchCopy.searchError
        }
    }
}

struct ImageSearchSheet: View {
    @Environment(\.dismiss) private var dismiss
    var onPick: (ImageHit) -> Void
    @State private var model: ImageSearchModel
    @State private var library = true
    @State private var query = ""

    init(client: EventsClient, onPick: @escaping (ImageHit) -> Void) {
        self.onPick = onPick
        _model = State(initialValue: ImageSearchModel(client: client))
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 12) {
                Picker(ImageSearchCopy.title, selection: $library) {
                    Text(ImageSearchCopy.library).tag(true)
                    Text(ImageSearchCopy.upload).tag(false)
                }
                .pickerStyle(.segmented)
                if library {
                    PDATextField(ImageSearchCopy.placeholder, text: $query, capitalization: .never)
                    if model.busy {
                        Text(ImageSearchCopy.searching)
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.muted)
                    }
                    if let empty = model.empty {
                        Text(empty).font(PDAType.control).foregroundStyle(PDAColor.muted)
                    }
                    if let error = model.error {
                        Text(error).font(PDAType.control).foregroundStyle(PDAColor.destructive)
                    }
                    ScrollView {
                        LazyVGrid(columns: [GridItem(.flexible()), GridItem(.flexible()), GridItem(.flexible())], spacing: 8) {
                            ForEach(model.results) { hit in
                                Button(hit.title.isEmpty ? "select image" : hit.title.lowercased()) {
                                    onPick(hit)
                                    dismiss()
                                }
                                .font(PDAType.control)
                                .foregroundStyle(PDAColor.foreground)
                                .frame(maxWidth: .infinity, minHeight: 72)
                                .background(PDAColor.surfaceDim, in: RoundedRectangle(cornerRadius: PDARadius.md))
                            }
                        }
                    }
                    if model.showsGiphyMark {
                        Text(ImageSearchCopy.attribution)
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.muted)
                    }
                } else {
                    Text(ImageSearchCopy.drop)
                        .font(PDAType.field)
                        .foregroundStyle(PDAColor.brand700)
                        .frame(maxWidth: .infinity, minHeight: 160)
                        .background(PDAColor.brand50, in: RoundedRectangle(cornerRadius: PDARadius.md))
                        .overlay {
                            RoundedRectangle(cornerRadius: PDARadius.md)
                                .strokeBorder(PDAColor.brand200, style: StrokeStyle(lineWidth: 2, dash: [6]))
                        }
                }
                HStack {
                    Spacer()
                    PDAButton(ImageSearchCopy.cancel, variant: .ghost) { dismiss() }
                }
            }
            .padding()
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(PDAColor.background)
            .navigationTitle(ImageSearchCopy.title)
            .navigationBarTitleDisplayMode(.inline)
        }
        .task { await model.search("") }
        .onChange(of: query) { _, next in
            Task { await model.search(next) }
        }
    }
}
