import SwiftUI

enum FlaggedEventsCopy {
    static let title = "flagged events"
    static let loading = "loading…"
    static let error = "couldn't load flags — try refreshing"
    static let empty = "nothing here 🌿"
    static let forbiddenTitle = "flagged events"
    static let forbiddenBody = "you need permission to manage events to see this list."
    static let filters = ["pending", "actioned", "dismissed", "all"]
}

enum FlaggedEventsError: Error, Equatable {
    case forbidden
}

struct FlaggedEventRow: Decodable, Equatable, Identifiable {
    let id: String
    let eventId: String
    let eventTitle: String
    let flaggedByName: String
    let reason: String
    let status: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id, reason, status
        case eventId = "event_id"
        case eventTitle = "event_title"
        case flaggedByName = "flagged_by_name"
        case createdAt = "created_at"
    }

    init(
        id: String,
        eventId: String,
        eventTitle: String,
        flaggedByName: String,
        reason: String,
        status: String,
        createdAt: String
    ) {
        self.id = id
        self.eventId = eventId
        self.eventTitle = eventTitle
        self.flaggedByName = flaggedByName
        self.reason = reason
        self.status = status
        self.createdAt = createdAt
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        eventId = try c.decodeIfPresent(String.self, forKey: .eventId) ?? ""
        eventTitle = try c.decodeIfPresent(String.self, forKey: .eventTitle) ?? ""
        flaggedByName = try c.decodeIfPresent(String.self, forKey: .flaggedByName) ?? ""
        reason = try c.decodeIfPresent(String.self, forKey: .reason) ?? ""
        status = try c.decodeIfPresent(String.self, forKey: .status) ?? ""
        createdAt = try c.decodeIfPresent(String.self, forKey: .createdAt) ?? ""
    }
}

func flaggedEventsURL(base: URL, status: String? = "pending") -> URL {
    let url = URL(string: "/api/community/event-flags/", relativeTo: base)!.absoluteURL
    guard let status, status != "all" else { return url }
    var comps = URLComponents(url: url, resolvingAgainstBaseURL: false)!
    comps.queryItems = [URLQueryItem(name: "status", value: status)]
    return comps.url!
}

func flaggedEventMeta(_ row: FlaggedEventRow) -> String {
    let when: String
    if let date = Event.parseISODate(row.createdAt) {
        when = formatEventDateTime(start: date, end: nil, datetimeTbd: false).lowercased()
    } else {
        when = row.createdAt.lowercased()
    }
    return "flagged by \(row.flaggedByName.lowercased()) · \(when)"
}

extension EventsClient {
    func flaggedEvents(status: String = "pending") async throws -> [FlaggedEventRow] {
        var req = URLRequest(url: flaggedEventsURL(base: baseURL, status: status))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let code = (response as? HTTPURLResponse)?.statusCode ?? 0
        if code == 403 { throw FlaggedEventsError.forbidden }
        guard (200 ..< 300).contains(code) else { throw APIError.http(code) }
        return try Event.decoder.decode([FlaggedEventRow].self, from: data)
    }
}

@Observable
final class FlaggedEventsModel {
    var client: EventsClient
    var rows: [FlaggedEventRow] = []
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { FlaggedEventsCopy.forbiddenTitle }
    var explanationBody: String { FlaggedEventsCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load(status: String = "pending") async {
        error = nil
        forbidden = false
        do {
            rows = try await client.flaggedEvents(status: status)
            loaded = true
        } catch FlaggedEventsError.forbidden {
            rows = []
            forbidden = true
            loaded = true
        } catch {
            rows = []
            self.error = FlaggedEventsCopy.error
            loaded = true
        }
    }
}

struct FlaggedEventsView: View {
    var client: EventsClient
    @State private var model: FlaggedEventsModel?
    @State private var filter = "pending"

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
                    PDAButton("try again") { Task { await model.load(status: filter) } }
                }
            } else if let model, model.loaded {
                VStack(spacing: 8) {
                    Picker("filter", selection: $filter) {
                        ForEach(FlaggedEventsCopy.filters, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    if model.rows.isEmpty {
                        ContentUnavailableView(FlaggedEventsCopy.empty, systemImage: "flag")
                    } else {
                        List(model.rows) { row in
                            VStack(alignment: .leading, spacing: 4) {
                                Text(row.eventTitle.lowercased())
                                Text(flaggedEventMeta(row)).font(.footnote).foregroundStyle(.secondary)
                                if !row.reason.isEmpty {
                                    Text(row.reason.lowercased())
                                }
                                Text(row.status.lowercased()).font(.caption).foregroundStyle(.secondary)
                            }
                        }
                    }
                }
            } else {
                ProgressView(FlaggedEventsCopy.loading)
            }
        }
        .navigationTitle(FlaggedEventsCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = FlaggedEventsModel(client: client) }
            await model?.load(status: filter)
        }
        .onChange(of: filter) { _, newValue in
            Task { await model?.load(status: newValue) }
        }
    }
}
