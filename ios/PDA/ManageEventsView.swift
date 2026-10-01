import SwiftUI

enum ManageEventsCopy {
    static let title = "manage events"
    static let loading = "loading…"
    static let error = "couldn't load events — try refreshing"
    static let empty = "nothing in this bucket"
    static let search = "title contains…"
    static let forbiddenTitle = "manage events"
    static let forbiddenBody = "you need permission to manage events to see this list."
    static let official = "official"
    static let club = "pda club"
    static let partiful = "partiful import · not on calendar"
    static let legacy = "legacy · not on calendar"
    static let buckets = ["upcoming", "past", "drafts", "cancelled"]
    static let sorts = ["date", "title", "type"]
}

enum ManageEventsError: Error, Equatable {
    case forbidden
}

struct ManageEventRow: Decodable, Equatable, Identifiable {
    let id: String
    let title: String
    let status: String
    let isPast: Bool
    let startDatetime: String
    let location: String
    let eventType: String
    let datetimeTbd: Bool
    let isPartifulImport: Bool
    let isLegacy: Bool

    enum CodingKeys: String, CodingKey {
        case id, title, status, location
        case isPast = "is_past"
        case startDatetime = "start_datetime"
        case eventType = "event_type"
        case datetimeTbd = "datetime_tbd"
        case isPartifulImport = "is_partiful_import"
        case isLegacy = "is_legacy"
    }

    init(
        id: String,
        title: String,
        status: String,
        isPast: Bool,
        startDatetime: String,
        location: String,
        eventType: String,
        datetimeTbd: Bool,
        isPartifulImport: Bool,
        isLegacy: Bool
    ) {
        self.id = id
        self.title = title
        self.status = status
        self.isPast = isPast
        self.startDatetime = startDatetime
        self.location = location
        self.eventType = eventType
        self.datetimeTbd = datetimeTbd
        self.isPartifulImport = isPartifulImport
        self.isLegacy = isLegacy
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        status = try c.decodeIfPresent(String.self, forKey: .status) ?? "active"
        isPast = try c.decodeIfPresent(Bool.self, forKey: .isPast) ?? false
        startDatetime = try c.decodeIfPresent(String.self, forKey: .startDatetime) ?? ""
        location = try c.decodeIfPresent(String.self, forKey: .location) ?? ""
        eventType = try c.decodeIfPresent(String.self, forKey: .eventType) ?? "community"
        datetimeTbd = try c.decodeIfPresent(Bool.self, forKey: .datetimeTbd) ?? false
        isPartifulImport = try c.decodeIfPresent(Bool.self, forKey: .isPartifulImport) ?? false
        isLegacy = try c.decodeIfPresent(Bool.self, forKey: .isLegacy) ?? false
    }
}

func manageEventsURL(base: URL) -> URL {
    eventsListURL(base: base)
}

func visibleManageEvents(
    _ rows: [ManageEventRow],
    bucket: String = "upcoming",
    sort: String = "date",
    query: String = ""
) -> [ManageEventRow] {
    let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    return rows
        .filter { manageEventInBucket($0, bucket) && ($0.title.lowercased().contains(q) || q.isEmpty) }
        .sorted { manageEventBefore($0, $1, sort) }
}

func manageEventsEmptyMessage() -> String {
    ManageEventsCopy.empty
}

func manageEventSubtitle(_ row: ManageEventRow) -> String {
    let when: String
    if row.datetimeTbd || row.startDatetime.isEmpty {
        when = "tbd"
    } else if let start = Event.parseISODate(row.startDatetime) {
        when = formatEventDateTime(start: start, end: nil, datetimeTbd: false).lowercased()
    } else {
        when = "tbd"
    }
    if row.location.isEmpty { return when }
    return "\(when) · \(row.location.lowercased())"
}

private func manageEventInBucket(_ row: ManageEventRow, _ bucket: String) -> Bool {
    switch bucket {
    case "past": row.status == "active" && row.isPast
    case "drafts": row.status == "draft"
    case "cancelled": row.status == "cancelled"
    default: row.status == "active" && !row.isPast
    }
}

private func manageEventBefore(_ a: ManageEventRow, _ b: ManageEventRow, _ sort: String) -> Bool {
    switch sort {
    case "title":
        return a.title.localizedCompare(b.title) == .orderedAscending
    case "type":
        let type = a.eventType.localizedCompare(b.eventType)
        if type != .orderedSame { return type == .orderedAscending }
        return a.title.localizedCompare(b.title) == .orderedAscending
    default:
        return a.startDatetime < b.startDatetime
    }
}

extension EventsClient {
    func manageEvents() async throws -> [ManageEventRow] {
        var req = URLRequest(url: manageEventsURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw ManageEventsError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([ManageEventRow].self, from: data)
    }
}

@Observable
final class ManageEventsModel {
    var client: EventsClient
    var rows: [ManageEventRow] = []
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { ManageEventsCopy.forbiddenTitle }
    var explanationBody: String { ManageEventsCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            rows = try await client.manageEvents()
            loaded = true
        } catch ManageEventsError.forbidden {
            rows = []
            forbidden = true
            loaded = true
        } catch {
            rows = []
            self.error = ManageEventsCopy.error
            loaded = true
        }
    }
}

struct ManageEventsView: View {
    var client: EventsClient
    @State private var model: ManageEventsModel?
    @State private var bucket = "upcoming"
    @State private var sort = "date"
    @State private var query = ""

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
            } else if let model, model.loaded {
                let rows = visibleManageEvents(model.rows, bucket: bucket, sort: sort, query: query)
                VStack(spacing: 8) {
                    Picker("bucket", selection: $bucket) {
                        ForEach(ManageEventsCopy.buckets, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    Picker("sort", selection: $sort) {
                        ForEach(ManageEventsCopy.sorts, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    if rows.isEmpty {
                        ContentUnavailableView(manageEventsEmptyMessage(), systemImage: "calendar")
                    } else {
                        List(rows) { row in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(row.title.lowercased())
                                Text(manageEventSubtitle(row)).font(.footnote).foregroundStyle(.secondary)
                                manageEventBadges(row)
                            }
                        }
                    }
                }
            } else {
                ProgressView(ManageEventsCopy.loading)
            }
        }
        .searchable(text: $query, prompt: ManageEventsCopy.search)
        .navigationTitle(ManageEventsCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = ManageEventsModel(client: client) }
            await model?.load()
        }
    }

    @ViewBuilder
    private func manageEventBadges(_ row: ManageEventRow) -> some View {
        HStack(spacing: 6) {
            if row.eventType == "official" {
                Text(ManageEventsCopy.official).font(.caption)
            }
            if row.eventType == "club" {
                Text(ManageEventsCopy.club).font(.caption)
            }
            if row.isPartifulImport {
                Text(ManageEventsCopy.partiful).font(.caption)
            }
            if row.isLegacy {
                Text(ManageEventsCopy.legacy).font(.caption)
            }
        }
        .foregroundStyle(.secondary)
    }
}
