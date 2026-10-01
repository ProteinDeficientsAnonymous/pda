import SwiftUI

enum SurveyResponsesCopy {
    static let responses = "responses"
    static let back = "← back to editor"
    static let empty = "no responses yet"
    static let loadError = "couldn't load responses — try refreshing"
    static let submittedBy = "submitted by"
    static let at = "at"
    static let pollTallies = "poll tallies"
    static let loadingTallies = "loading tallies…"
    static let talliesError = "couldn't load tallies"
    static let option = "option"
    static let yes = "yes"
    static let maybe = "maybe"
    static let finalize = "finalize poll"
    static let finalizeTitle = "finalize survey poll"
    static let finalizeBody = "pick the winning datetime. this locks the survey and, if linked, updates the event start time."
    static let cancel = "cancel"
    static let confirm = "confirm"
    static let finalizing = "finalizing…"
    static let invalidOption = "pick a valid option"
    static let finalized = "poll finalized 🌱"
    static let requestFailed = "request failed"
}

struct SurveyStoredAnswer: Decodable, Equatable {
    let answer: SurveyAnswerValue
}

struct SurveyResponseRecord: Decodable, Equatable, Identifiable {
    let id: String
    let userId: String?
    let userName: String?
    let answers: [String: SurveyStoredAnswer]
    let submittedAt: String

    enum CodingKeys: String, CodingKey {
        case id, answers
        case userId = "user_id"
        case userName = "user_name"
        case submittedAt = "submitted_at"
    }
}

struct SurveyPollTally: Decodable, Equatable, Identifiable {
    var id: String { questionId }
    let questionId: String
    let tallies: [String: [String: Int]]
    let totalResponses: Int

    enum CodingKeys: String, CodingKey {
        case questionId = "question_id"
        case tallies
        case totalResponses = "total_responses"
    }
}

func surveyResponseCountLabel(_ count: Int) -> String {
    "\(count) response\(count == 1 ? "" : "s")"
}

func surveyResponseSubmitter(_ name: String?) -> String {
    name ?? "—"
}

func surveyResponseAnswerText(_ answer: SurveyAnswerValue?) -> String {
    guard let answer else { return "—" }
    switch answer {
    case .text(let text):
        return text
    case .map(let pairs):
        return pairs.map { "\($0.key): \($0.value)" }.joined(separator: "\n")
    }
}

func surveyResponseSubmittedAt(_ raw: String) -> String {
    guard let date = Event.parseISODate(raw) else { return raw.lowercased() }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.dateFormat = "MMM d, yyyy h:mm a"
    return formatter.string(from: date).lowercased()
}

func surveyPollCount(_ counts: [String: Int], _ key: String) -> Int {
    counts[key] ?? 0
}

func surveyPollTallyTotal(_ count: Int) -> String {
    "total responses recorded: \(count)"
}

func surveyPollTallyTitle(questionId: String, questions: [PublicSurveyQuestion]) -> String {
    (questions.first { $0.id == questionId }?.label ?? questionId).lowercased()
}

func surveyFinalizeOptions(_ survey: AdminSurveyDetail) -> [String]? {
    guard survey.pollResult == nil else { return nil }
    guard let question = survey.questions.first(where: { $0.fieldType == "datetime_poll" }),
          !question.options.isEmpty
    else { return nil }
    return question.options
}

func surveyFinalizeWinningDatetime(_ option: String) -> String? {
    guard let date = Event.parseISODate(option) else { return nil }
    let formatter = ISO8601DateFormatter()
    formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
    formatter.timeZone = TimeZone(secondsFromGMT: 0)
    return formatter.string(from: date)
}

func surveyResponsesURL(base: URL, surveyId: String) -> URL {
    let encoded = surveyId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? surveyId
    return URL(string: "/api/community/surveys/\(encoded)/responses/", relativeTo: base)!.absoluteURL
}

func surveyPollTalliesURL(base: URL, surveyId: String) -> URL {
    let encoded = surveyId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? surveyId
    return URL(string: "/api/community/surveys/\(encoded)/tallies/", relativeTo: base)!.absoluteURL
}

func surveyFinalizeURL(base: URL, surveyId: String) -> URL {
    let encoded = surveyId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? surveyId
    return URL(string: "/api/community/surveys/\(encoded)/finalize/", relativeTo: base)!.absoluteURL
}

extension EventsClient {
    func surveyResponses(id: String) async throws -> [SurveyResponseRecord] {
        let (data, status) = try await surveyGET(surveyResponsesURL(base: baseURL, surveyId: id))
        guard (200 ..< 300).contains(status) else { throw addSurveyQuestionError(data: data) }
        return try Event.decoder.decode([SurveyResponseRecord].self, from: data)
    }

    func surveyPollTallies(id: String) async throws -> [SurveyPollTally] {
        let (data, status) = try await surveyGET(surveyPollTalliesURL(base: baseURL, surveyId: id))
        guard (200 ..< 300).contains(status) else { throw addSurveyQuestionError(data: data) }
        return try Event.decoder.decode([SurveyPollTally].self, from: data)
    }

    func finalizeSurveyPoll(surveyId: String, winningDatetime: String) async throws {
        var req = URLRequest(url: surveyFinalizeURL(base: baseURL, surveyId: surveyId))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: ["winning_datetime": winningDatetime])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw addSurveyQuestionError(data: data) }
    }

    private func surveyGET(_ url: URL) async throws -> (Data, Int) {
        var req = URLRequest(url: url)
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        return (data, status)
    }
}

@Observable
final class SurveyResponsesModel {
    var client: EventsClient
    var surveyId: String
    var survey: AdminSurveyDetail?
    var responses: [SurveyResponseRecord] = []
    var tallies: [SurveyPollTally] = []
    var error: String?
    var talliesError: String?
    var talliesLoading = false
    var notice: String?
    var finalizeError: String?
    var finalizeChoice = ""
    var showFinalize = false
    var finalizing = false
    var loaded = false

    init(client: EventsClient, surveyId: String) {
        self.client = client
        self.surveyId = surveyId
    }

    func load() async {
        do {
            async let surveyTask = client.adminSurvey(id: surveyId)
            async let responsesTask = client.surveyResponses(id: surveyId)
            let loadedSurvey = try await surveyTask
            let loadedResponses = try await responsesTask
            survey = loadedSurvey
            responses = loadedResponses
            error = nil
            loaded = true
            await loadTallies(for: loadedSurvey)
        } catch {
            survey = nil
            responses = []
            tallies = []
            self.error = SurveyResponsesCopy.loadError
            loaded = true
        }
    }

    func finalize(_ option: String) async {
        guard let iso = surveyFinalizeWinningDatetime(option) else {
            finalizeError = SurveyResponsesCopy.invalidOption
            return
        }
        finalizing = true
        finalizeError = nil
        do {
            try await client.finalizeSurveyPoll(surveyId: surveyId, winningDatetime: iso)
            notice = SurveyResponsesCopy.finalized
            showFinalize = false
            finalizing = false
            await load()
        } catch AddSurveyQuestionError.forbidden {
            finalizeError = AddSurveyQuestionCopy.forbidden
            finalizing = false
        } catch AddSurveyQuestionError.notFound {
            finalizeError = AddSurveyQuestionCopy.notFound
            finalizing = false
        } catch {
            finalizeError = SurveyResponsesCopy.requestFailed
            finalizing = false
        }
    }

    private func loadTallies(for survey: AdminSurveyDetail) async {
        guard survey.questions.contains(where: { $0.fieldType == "datetime_poll" }) else {
            tallies = []
            talliesError = nil
            talliesLoading = false
            return
        }
        talliesLoading = true
        do {
            tallies = try await client.surveyPollTallies(id: surveyId)
            talliesError = nil
        } catch {
            tallies = []
            talliesError = SurveyResponsesCopy.talliesError
        }
        talliesLoading = false
    }
}

struct SurveyResponsesView: View {
    let surveyId: String
    var client: EventsClient
    @Environment(\.dismiss) private var dismiss
    @State private var model: SurveyResponsesModel?

    var body: some View {
        Group {
            if let model, let error = model.error {
                Text(error)
                    .font(PDAType.field)
                    .foregroundStyle(PDAColor.foregroundSecondary)
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
            } else if let model, model.loaded, let survey = model.survey {
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(survey.title.lowercased())
                            .font(PDAType.field)
                            .fontWeight(.medium)
                            .foregroundStyle(PDAColor.foreground)
                        Text(surveyResponseCountLabel(model.responses.count))
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.muted)
                        PDAButton(SurveyResponsesCopy.back, variant: .ghost) { dismiss() }
                        if let notice = model.notice {
                            Text(notice)
                                .font(PDAType.control)
                                .foregroundStyle(PDAColor.foregroundSecondary)
                        }
                        if survey.questions.contains(where: { $0.fieldType == "datetime_poll" }) {
                            talliesSection(survey, model: model)
                        }
                        if model.responses.isEmpty {
                            Text(SurveyResponsesCopy.empty)
                                .font(PDAType.control)
                                .foregroundStyle(PDAColor.muted)
                        } else {
                            ForEach(model.responses) { response in
                                responseCard(response, questions: survey.questions)
                            }
                        }
                    }
                    .padding()
                }
            } else {
                ProgressView(AdminSurveysCopy.loading)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(PDAColor.background)
        .navigationTitle(SurveyResponsesCopy.responses)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: showFinalize) {
            finalizeSheet
        }
        .task {
            if model == nil { model = SurveyResponsesModel(client: client, surveyId: surveyId) }
            await model?.load()
        }
    }

    private var showFinalize: Binding<Bool> {
        Binding(
            get: { model?.showFinalize ?? false },
            set: { model?.showFinalize = $0 }
        )
    }

    @ViewBuilder
    private func talliesSection(_ survey: AdminSurveyDetail, model: SurveyResponsesModel) -> some View {
        Text(SurveyResponsesCopy.pollTallies)
            .font(PDAType.control)
            .foregroundStyle(PDAColor.muted)
        if model.talliesLoading {
            Text(SurveyResponsesCopy.loadingTallies)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
        } else if let talliesError = model.talliesError {
            Text(talliesError)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
        } else {
            ForEach(model.tallies) { row in
                tallyCard(row, questions: survey.questions)
            }
        }
        if let options = surveyFinalizeOptions(survey) {
            PDAButton(SurveyResponsesCopy.finalize, variant: .secondary) {
                model.finalizeChoice = options.first ?? ""
                model.finalizeError = nil
                model.showFinalize = true
            }
        }
    }

    private func tallyCard(_ row: SurveyPollTally, questions: [PublicSurveyQuestion]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(surveyPollTallyTitle(questionId: row.questionId, questions: questions))
                .font(PDAType.control)
                .fontWeight(.medium)
                .foregroundStyle(PDAColor.foreground)
            Text(surveyPollTallyTotal(row.totalResponses))
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
            Text("\(SurveyResponsesCopy.option) · \(SurveyResponsesCopy.yes) · \(SurveyResponsesCopy.maybe)")
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
            ForEach(row.tallies.keys.sorted(), id: \.self) { option in
                let counts = row.tallies[option] ?? [:]
                Text(
                    "\(surveyResponseSubmittedAt(option)) · \(surveyPollCount(counts, "yes")) · \(surveyPollCount(counts, "maybe"))"
                )
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.lg))
        .overlay {
            RoundedRectangle(cornerRadius: PDARadius.lg)
                .strokeBorder(PDAColor.border, lineWidth: 1)
        }
    }

    private func responseCard(_ response: SurveyResponseRecord, questions: [PublicSurveyQuestion]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            labeled(SurveyResponsesCopy.submittedBy, surveyResponseSubmitter(response.userName))
            labeled(SurveyResponsesCopy.at, surveyResponseSubmittedAt(response.submittedAt))
            ForEach(questions) { question in
                labeled(question.label, surveyResponseAnswerText(response.answers[question.id]?.answer))
            }
        }
        .padding(12)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.lg))
        .overlay {
            RoundedRectangle(cornerRadius: PDARadius.lg)
                .strokeBorder(PDAColor.border, lineWidth: 1)
        }
    }

    private func labeled(_ label: String, _ value: String) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(label)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.muted)
            Text(value)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
        }
    }

    @ViewBuilder
    private var finalizeSheet: some View {
        if let model, let survey = model.survey, let options = surveyFinalizeOptions(survey) {
            NavigationStack {
                ScrollView {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(SurveyResponsesCopy.finalizeBody)
                            .font(PDAType.field)
                            .foregroundStyle(PDAColor.muted)
                        ForEach(options, id: \.self) { option in
                            PDAButton(
                                surveyResponseSubmittedAt(option),
                                variant: model.finalizeChoice == option ? .secondary : .ghost
                            ) {
                                model.finalizeChoice = option
                            }
                        }
                        if let finalizeError = model.finalizeError {
                            Text(finalizeError)
                                .font(PDAType.control)
                                .foregroundStyle(PDAColor.destructive)
                        }
                        HStack {
                            Spacer()
                            PDAButton(SurveyResponsesCopy.cancel, variant: .ghost) { model.showFinalize = false }
                                .disabled(model.finalizing)
                            PDAButton(model.finalizing ? SurveyResponsesCopy.finalizing : SurveyResponsesCopy.confirm) {
                                Task { await model.finalize(model.finalizeChoice) }
                            }
                            .disabled(model.finalizing)
                        }
                    }
                    .padding()
                }
                .background(PDAColor.background)
                .navigationTitle(SurveyResponsesCopy.finalizeTitle)
                .navigationBarTitleDisplayMode(.inline)
            }
        }
    }
}
