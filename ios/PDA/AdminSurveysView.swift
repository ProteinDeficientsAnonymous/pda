import SwiftUI

enum AdminSurveysCopy {
    static let title = "surveys"
    static let loading = "loading…"
    static let error = "couldn't load surveys — try refreshing"
    static let empty = "nothing yet"
    static let forbiddenTitle = "surveys"
    static let forbiddenBody = "you need permission to manage surveys to see this list."
}

enum AdminSurveysError: Error, Equatable {
    case forbidden
}

struct AdminSurveySummary: Decodable, Equatable, Identifiable {
    let id: String
    let title: String
    let slug: String
    let visibility: String
    let isActive: Bool
    let linkedEventId: String?
    let createdAt: String
    let responseCount: Int

    private enum CodingKeys: String, CodingKey {
        case id, title, slug, visibility
        case isActive = "is_active"
        case linkedEventId = "linked_event_id"
        case createdAt = "created_at"
        case responseCount = "response_count"
    }
}

func adminSurveysURL(base: URL) -> URL {
    URL(string: "/api/community/surveys/admin/", relativeTo: base)!.absoluteURL
}

func adminSurveyStatus(_ survey: AdminSurveySummary) -> String {
    survey.isActive ? "active" : "closed"
}

func adminSurveyRowLine(_ survey: AdminSurveySummary) -> String {
    "/\(survey.slug) · \(survey.visibility) · \(survey.responseCount) responses · \(adminSurveyDate(survey.createdAt))"
}

func adminSurveyDate(_ raw: String) -> String {
    guard let date = Event.parseISODate(raw) else { return raw.lowercased() }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = TimeZone(secondsFromGMT: 0)
    formatter.dateFormat = "MMM d, yyyy"
    return formatter.string(from: date).lowercased()
}

extension EventsClient {
    func adminSurveys() async throws -> [AdminSurveySummary] {
        var req = URLRequest(url: adminSurveysURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw AdminSurveysError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([AdminSurveySummary].self, from: data)
    }
}

@Observable
final class AdminSurveysModel {
    var client: EventsClient
    var surveys: [AdminSurveySummary] = []
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { AdminSurveysCopy.forbiddenTitle }
    var explanationBody: String { AdminSurveysCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            surveys = try await client.adminSurveys()
            loaded = true
        } catch AdminSurveysError.forbidden {
            surveys = []
            forbidden = true
            loaded = true
        } catch {
            surveys = []
            self.error = AdminSurveysCopy.error
            loaded = true
        }
    }
}

struct AdminSurveysView: View {
    var client: EventsClient
    @State private var model: AdminSurveysModel?
    @State private var showCreate = false

    var body: some View {
        Group {
            if let model, model.forbidden {
                VStack(alignment: .leading, spacing: 12) {
                    Text(model.explanationTitle).font(PDAType.field).fontWeight(.medium)
                    Text(model.explanationBody)
                        .font(PDAType.field)
                        .foregroundStyle(PDAColor.foregroundSecondary)
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
                if model.surveys.isEmpty {
                    ContentUnavailableView(AdminSurveysCopy.empty, systemImage: "list.bullet")
                } else {
                    ScrollView {
                        VStack(alignment: .leading, spacing: 8) {
                            ForEach(model.surveys) { survey in
                                NavigationLink {
                                    SurveyQuestionsView(surveyId: survey.id, client: client)
                                } label: {
                                    AdminSurveyRow(survey: survey)
                                }
                            }
                        }
                        .padding()
                    }
                }
            } else {
                ProgressView(AdminSurveysCopy.loading)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(PDAColor.background)
        .navigationTitle(AdminSurveysCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let model, model.loaded, !model.forbidden, model.error == nil {
                ToolbarItem(placement: .topBarTrailing) {
                    PDAButton(CreateSurveyCopy.button) { showCreate = true }
                }
            }
        }
        .sheet(isPresented: $showCreate) {
            CreateSurveySheet(client: client) {
                showCreate = false
                Task { await model?.load() }
            }
        }
        .task {
            if model == nil { model = AdminSurveysModel(client: client) }
            await model?.load()
        }
    }
}

private struct AdminSurveyRow: View {
    let survey: AdminSurveySummary

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(survey.title.lowercased())
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            Text(adminSurveyRowLine(survey))
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
            Text(adminSurveyStatus(survey))
                .font(PDAType.control)
                .foregroundStyle(survey.isActive ? PDAColor.success : PDAColor.foregroundSecondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 2)
                .background(
                    survey.isActive ? PDAColor.successSubtle : PDAColor.surfaceRaised,
                    in: Capsule()
                )
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.lg))
        .overlay {
            RoundedRectangle(cornerRadius: PDARadius.lg)
                .strokeBorder(PDAColor.border, lineWidth: 1)
        }
    }
}
