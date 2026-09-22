import SwiftUI

enum AttendanceReportCopy {
    static let title = "attendance"
    static let subtitle = "who actually showed up, per event and per member"
    static let loading = "loading…"
    static let error = "couldn't load attendance — try refreshing"
    static let empty = "no attendance marked yet 🌿"
    static let attended = "attended"
    static let noShow = "no-show"
    static let dateTbd = "date tbd"
    static let forbiddenTitle = "attendance"
    static let forbiddenBody = "you need permission to manage events to see this list."
}

enum AttendanceReportError: Error, Equatable {
    case forbidden
}

struct AttendanceEventRow: Decodable, Equatable, Identifiable {
    var id: String { eventId }
    let eventId: String
    let title: String
    let eventType: String
    let startDatetime: String
    let attendedCount: Int
    let noShowCount: Int
    let goingCount: Int

    enum CodingKeys: String, CodingKey {
        case title
        case eventId = "event_id"
        case eventType = "event_type"
        case startDatetime = "start_datetime"
        case attendedCount = "attended_count"
        case noShowCount = "no_show_count"
        case goingCount = "going_count"
    }

    init(
        eventId: String,
        title: String,
        eventType: String,
        startDatetime: String,
        attendedCount: Int,
        noShowCount: Int,
        goingCount: Int
    ) {
        self.eventId = eventId
        self.title = title
        self.eventType = eventType
        self.startDatetime = startDatetime
        self.attendedCount = attendedCount
        self.noShowCount = noShowCount
        self.goingCount = goingCount
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        eventId = try c.decode(String.self, forKey: .eventId)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        eventType = try c.decodeIfPresent(String.self, forKey: .eventType) ?? ""
        startDatetime = try c.decodeIfPresent(String.self, forKey: .startDatetime) ?? ""
        attendedCount = try c.decodeIfPresent(Int.self, forKey: .attendedCount) ?? 0
        noShowCount = try c.decodeIfPresent(Int.self, forKey: .noShowCount) ?? 0
        goingCount = try c.decodeIfPresent(Int.self, forKey: .goingCount) ?? 0
    }
}

struct AttendanceReport: Decodable, Equatable {
    let events: [AttendanceEventRow]
    let officialNoShowCount: Int
    let clubNoShowCount: Int

    enum CodingKeys: String, CodingKey {
        case events
        case officialNoShowCount = "official_no_show_count"
        case clubNoShowCount = "club_no_show_count"
    }
}

func attendanceReportURL(base: URL) -> URL {
    URL(string: "/api/community/events/attendance-report/", relativeTo: base)!.absoluteURL
}

func attendanceRowsLink(flags: [String: Bool]) -> Bool {
    flags["host_attendance_report"] == true
}

func attendanceEventWhen(_ row: AttendanceEventRow) -> String {
    guard let date = Event.parseISODate(row.startDatetime) else { return AttendanceReportCopy.dateTbd }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.setLocalizedDateFormatFromTemplate("EEEMMMdyyyy")
    return formatter.string(from: date).lowercased()
}

func attendanceStat(_ label: String, _ value: Int) -> String {
    "\(value) \(label)"
}

extension EventsClient {
    func attendanceReport() async throws -> AttendanceReport {
        var req = URLRequest(url: attendanceReportURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw AttendanceReportError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(AttendanceReport.self, from: data)
    }
}

@Observable
final class AttendanceReportModel {
    var client: EventsClient
    var rows: [AttendanceEventRow] = []
    var forbidden = false
    var linksEnabled = false
    var error: String?
    var loaded = false

    var explanationTitle: String { AttendanceReportCopy.forbiddenTitle }
    var explanationBody: String { AttendanceReportCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            let report = try await client.attendanceReport()
            rows = report.events
            linksEnabled = attendanceRowsLink(flags: (try? await client.featureFlags()) ?? [:])
            loaded = true
        } catch AttendanceReportError.forbidden {
            rows = []
            linksEnabled = false
            forbidden = true
            loaded = true
        } catch {
            rows = []
            linksEnabled = false
            self.error = AttendanceReportCopy.error
            loaded = true
        }
    }
}

struct AttendanceReportView: View {
    var client: EventsClient
    @State private var model: AttendanceReportModel?

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
                VStack(alignment: .leading, spacing: 8) {
                    Text(AttendanceReportCopy.subtitle)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal)
                    if model.rows.isEmpty {
                        ContentUnavailableView(AttendanceReportCopy.empty, systemImage: "person.3")
                    } else {
                        List(model.rows) { row in
                            if model.linksEnabled {
                                NavigationLink {
                                    CheckInReportView(eventId: row.eventId, client: client)
                                } label: {
                                    attendanceRow(row)
                                }
                            } else {
                                attendanceRow(row)
                            }
                        }
                    }
                }
            } else {
                ProgressView(AttendanceReportCopy.loading)
            }
        }
        .navigationTitle(AttendanceReportCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = AttendanceReportModel(client: client) }
            await model?.load()
        }
    }

    private func attendanceRow(_ row: AttendanceEventRow) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(row.title.lowercased())
            Text(attendanceEventWhen(row)).font(.footnote).foregroundStyle(.secondary)
            HStack(spacing: 8) {
                Text(attendanceStat(AttendanceReportCopy.attended, row.attendedCount))
                Text(attendanceStat(AttendanceReportCopy.noShow, row.noShowCount))
            }
            .font(.caption)
            .foregroundStyle(.secondary)
        }
    }
}
