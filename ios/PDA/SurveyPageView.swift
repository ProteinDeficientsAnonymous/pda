import SwiftUI

enum SurveyPageCopy {
    static let loading = "loading…"
    static let loadError = "couldn't load the survey — try refreshing"
    static let closed = "this survey is closed — responses are no longer accepted"
    static let finalized = "this poll has been finalized — responses are locked"
    static let submit = "submit"
    static let update = "update response"
    static let saving = "saving…"
    static let saved = "saved ✓"
    static let required = "required"
    static let pickOne = "pick at least one"
    static let selectOne = "select one"
    static let submitError = "couldn't submit — try again"
}

enum SurveyAnswerValue: Equatable, Decodable {
    case text(String)
    case map([String: String])

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if let text = try? container.decode(String.self) {
            self = .text(text)
            return
        }
        self = .map(try container.decode([String: String].self))
    }
}

struct PublicSurveyQuestion: Decodable, Equatable, Identifiable {
    let id: String
    let label: String
    let fieldType: String
    let options: [String]
    let required: Bool
    let displayOrder: Int

    init(id: String, label: String, fieldType: String, options: [String], required: Bool, displayOrder: Int) {
        self.id = id
        self.label = label
        self.fieldType = fieldType
        self.options = options
        self.required = required
        self.displayOrder = displayOrder
    }

    enum CodingKeys: String, CodingKey {
        case id, label, options, required
        case fieldType = "field_type"
        case displayOrder = "display_order"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        label = try c.decodeIfPresent(String.self, forKey: .label) ?? ""
        fieldType = try c.decodeIfPresent(String.self, forKey: .fieldType) ?? "text"
        options = try c.decodeIfPresent([String].self, forKey: .options) ?? []
        required = try c.decodeIfPresent(Bool.self, forKey: .required) ?? false
        displayOrder = try c.decodeIfPresent(Int.self, forKey: .displayOrder) ?? 0
    }
}

struct PublicSurveyPollResult: Decodable, Equatable {
    let id: String
}

struct PublicSurvey: Decodable, Equatable {
    let id: String
    let title: String
    let description: String
    let slug: String
    let visibility: String
    let isActive: Bool
    let questions: [PublicSurveyQuestion]
    let myResponseId: String?
    let myAnswers: [String: SurveyAnswerValue]

    enum CodingKeys: String, CodingKey {
        case id, title, description, slug, visibility, questions
        case isActive = "is_active"
        case myResponseId = "my_response_id"
        case myAnswers = "my_answers"
        case pollResult = "poll_result"
    }

    let pollResult: PublicSurveyPollResult?

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        description = try c.decodeIfPresent(String.self, forKey: .description) ?? ""
        slug = try c.decodeIfPresent(String.self, forKey: .slug) ?? ""
        visibility = try c.decodeIfPresent(String.self, forKey: .visibility) ?? ""
        isActive = try c.decodeIfPresent(Bool.self, forKey: .isActive) ?? false
        questions = (try c.decodeIfPresent([PublicSurveyQuestion].self, forKey: .questions) ?? [])
            .sorted { $0.displayOrder < $1.displayOrder }
        myResponseId = try c.decodeIfPresent(String.self, forKey: .myResponseId)
        let stored = try c.decodeIfPresent([String: SurveyMyAnswer].self, forKey: .myAnswers) ?? [:]
        myAnswers = stored.mapValues(\.answer)
        pollResult = try c.decodeIfPresent(PublicSurveyPollResult.self, forKey: .pollResult)
    }
}

private struct SurveyMyAnswer: Decodable {
    let answer: SurveyAnswerValue
}

enum SurveySubmitError: Error {
    case rejected(String?)
}

func publicSurveyURL(base: URL, slug: String) -> URL {
    URL(string: "/api/community/surveys/view/\(slug)/", relativeTo: base)!.absoluteURL
}

func publicSurveyRespondURL(base: URL, slug: String) -> URL {
    URL(string: "/api/community/surveys/view/\(slug)/respond/", relativeTo: base)!.absoluteURL
}

func surveyAnswerError(_ question: PublicSurveyQuestion, answer: SurveyAnswerValue?) -> String? {
    guard question.required else { return nil }
    guard let answer else { return SurveyPageCopy.required }
    switch answer {
    case let .text(value):
        return value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? SurveyPageCopy.required : nil
    case let .map(value):
        return value.isEmpty ? SurveyPageCopy.pickOne : nil
    }
}

func surveyShowsClosed(_ survey: PublicSurvey) -> Bool {
    !survey.isActive && survey.pollResult == nil
}

private func surveyErrorCode(_ data: Data) -> String? {
    let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
    let detail = json?["detail"] as? [[String: Any]]
    return detail?.first?["code"] as? String
}

extension EventsClient {
    func publicSurvey(slug: String) async throws -> PublicSurvey {
        var req = URLRequest(url: publicSurveyURL(base: baseURL, slug: slug))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(PublicSurvey.self, from: data)
    }

    func submitPublicSurvey(slug: String, answers: [String: Any]) async throws {
        var req = URLRequest(url: publicSurveyRespondURL(base: baseURL, slug: slug))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: ["answers": answers])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else {
            throw SurveySubmitError.rejected(surveyErrorCode(data))
        }
    }
}

@Observable
final class SurveyPageModel {
    var client: EventsClient
    let slug: String
    var survey: PublicSurvey?
    var answers: [String: SurveyAnswerValue] = [:]
    var loadError: String?
    var serverError: String?
    var fieldErrors: [String: String] = [:]
    var saving = false
    var saved = false
    private var hydrated = false

    var showsClosed: Bool { survey.map(surveyShowsClosed) ?? false }
    var showsForm: Bool { survey != nil && !showsClosed }
    var readOnly: Bool { survey?.pollResult != nil }

    var submitLabel: String {
        if saving { return SurveyPageCopy.saving }
        return survey?.myResponseId == nil ? SurveyPageCopy.submit : SurveyPageCopy.update
    }

    init(slug: String, client: EventsClient = EventsClient()) {
        self.slug = slug
        self.client = client
    }

    func load() async {
        await fetch(resetOnError: true)
    }

    func reload() async {
        await fetch(resetOnError: false)
    }

    func setText(_ id: String, _ value: String) {
        answers[id] = .text(value)
    }

    func textAnswer(_ id: String) -> String {
        if case let .text(value) = answers[id] { return value }
        return ""
    }

    func setMap(_ id: String, _ value: [String: String]) {
        answers[id] = .map(value)
    }

    func mapAnswer(_ id: String) -> [String: String] {
        if case let .map(value) = answers[id] { return value }
        return [:]
    }

    func submit() async {
        guard let survey, !readOnly else { return }
        serverError = nil
        var next: [String: String] = [:]
        for question in survey.questions {
            if let error = surveyAnswerError(question, answer: answers[question.id]) {
                next[question.id] = error
            }
        }
        fieldErrors = next
        if !next.isEmpty { return }
        saving = true
        defer { saving = false }
        saved = false
        do {
            try await client.submitPublicSurvey(slug: slug, answers: surveyPayload())
            saved = true
        } catch let SurveySubmitError.rejected(code) {
            serverError = code == "survey.closed" ? SurveyPageCopy.closed : SurveyPageCopy.submitError
            if code == "survey.closed" { await reload() }
        } catch {
            serverError = SurveyPageCopy.submitError
        }
    }

    private func fetch(resetOnError: Bool) async {
        do {
            let next = try await client.publicSurvey(slug: slug)
            survey = next
            loadError = nil
            if !hydrated {
                answers = next.myAnswers
                hydrated = true
            }
        } catch {
            if resetOnError {
                survey = nil
                loadError = SurveyPageCopy.loadError
            }
        }
    }

    private func surveyPayload() -> [String: Any] {
        var payload: [String: Any] = [:]
        for (id, answer) in answers {
            switch answer {
            case let .text(value):
                if value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty { continue }
                payload[id] = value
            case let .map(value):
                if value.isEmpty { continue }
                payload[id] = value
            }
        }
        return payload
    }
}

struct SurveyPageView: View {
    let slug: String
    var client: EventsClient
    @State private var model: SurveyPageModel?

    var body: some View {
        Group {
            if let model, let loadError = model.loadError {
                ContentUnavailableView {
                    Label(loadError, systemImage: "exclamationmark.triangle")
                } actions: {
                    PDAButton("try again") { Task { await model.load() } }
                }
            } else if let model, let survey = model.survey, model.showsClosed {
                closed(survey)
            } else if let model, let survey = model.survey, model.showsForm {
                form(model, survey)
            } else {
                ProgressView(SurveyPageCopy.loading)
            }
        }
        .navigationTitle((model?.survey?.title ?? "survey").lowercased())
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = SurveyPageModel(slug: slug, client: client) }
            await model?.load()
        }
    }

    private func closed(_ survey: PublicSurvey) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(survey.title.lowercased())
                .font(PDAType.field)
                .foregroundStyle(PDAColor.foreground)
            if !survey.description.isEmpty {
                Text(survey.description.lowercased())
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foregroundTertiary)
            }
            Text(SurveyPageCopy.closed)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foregroundSecondary)
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
                .background(PDAColor.surfaceDim, in: RoundedRectangle(cornerRadius: PDARadius.md))
            Spacer()
        }
        .padding()
    }

    private func form(_ model: SurveyPageModel, _ survey: PublicSurvey) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                Text(survey.title.lowercased())
                    .font(PDAType.field)
                    .foregroundStyle(PDAColor.foreground)
                if !survey.description.isEmpty {
                    Text(survey.description.lowercased())
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.foregroundTertiary)
                }
                if model.readOnly {
                    Text(SurveyPageCopy.finalized)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.foregroundSecondary)
                        .padding(12)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .background(PDAColor.surfaceDim, in: RoundedRectangle(cornerRadius: PDARadius.md))
                }
                ForEach(survey.questions) { question in
                    questionField(model, question)
                }
                if let serverError = model.serverError {
                    Text(serverError)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.destructive)
                }
                if !model.readOnly {
                    PDAButton(model.submitLabel) { Task { await model.submit() } }
                        .disabled(model.saving)
                }
                if model.saved, !model.readOnly {
                    Text(SurveyPageCopy.saved)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.brand600)
                }
            }
            .padding()
        }
    }

    @ViewBuilder
    private func questionField(_ model: SurveyPageModel, _ question: PublicSurveyQuestion) -> some View {
        let label = surveyQuestionLabel(question)
        VStack(alignment: .leading, spacing: 8) {
            switch question.fieldType {
            case "textarea":
                PDATextField(
                    label,
                    text: textBinding(model, question.id),
                    axis: .vertical,
                    capitalization: .never,
                    lineLimit: 5
                )
                .disabled(model.readOnly)
            case "number":
                PDATextField(label, text: textBinding(model, question.id), keyboard: .decimalPad)
                    .disabled(model.readOnly)
            case "select":
                Picker(label, selection: textBinding(model, question.id)) {
                    Text(SurveyPageCopy.selectOne).tag("")
                    ForEach(question.options, id: \.self) { option in
                        Text(option.lowercased()).tag(option)
                    }
                }
                .disabled(model.readOnly)
            case "radio", "boolean":
                choiceList(model, question, options: question.fieldType == "boolean" ? ["yes", "no"] : question.options)
            case "checkbox":
                checkboxList(model, question)
            case "rating":
                ratingList(model, question)
            case "datetime_poll":
                pollList(model, question)
            default:
                PDATextField(label, text: textBinding(model, question.id), capitalization: .never)
                    .disabled(model.readOnly)
            }
            if let error = model.fieldErrors[question.id] {
                Text(error)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.destructive)
            }
        }
    }

    private func choiceList(_ model: SurveyPageModel, _ question: PublicSurveyQuestion, options: [String]) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(surveyQuestionLabel(question))
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            ForEach(options, id: \.self) { option in
                PDAButton(option.lowercased(), variant: model.textAnswer(question.id) == option ? .primary : .secondary) {
                    model.setText(question.id, option)
                }
                .disabled(model.readOnly)
            }
        }
    }

    private func checkboxList(_ model: SurveyPageModel, _ question: PublicSurveyQuestion) -> some View {
        let selected = Set(model.textAnswer(question.id).split(separator: ",").map(String.init))
        return VStack(alignment: .leading, spacing: 8) {
            Text(surveyQuestionLabel(question))
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            ForEach(question.options, id: \.self) { option in
                Toggle(option.lowercased(), isOn: Binding(
                    get: { selected.contains(option) },
                    set: { on in
                        var next = selected
                        if on { next.insert(option) } else { next.remove(option) }
                        model.setText(question.id, next.sorted().joined(separator: ","))
                    }
                ))
                .font(PDAType.control)
                .tint(PDAColor.brand600)
                .disabled(model.readOnly)
            }
        }
    }

    private func ratingList(_ model: SurveyPageModel, _ question: PublicSurveyQuestion) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(surveyQuestionLabel(question))
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            HStack {
                ForEach(1 ... 5, id: \.self) { star in
                    let on = (Int(model.textAnswer(question.id)) ?? 0) >= star
                    PDAButton(on ? "★" : "☆", variant: .ghost) {
                        model.setText(question.id, String(star))
                    }
                    .disabled(model.readOnly)
                }
            }
        }
    }

    private func pollList(_ model: SurveyPageModel, _ question: PublicSurveyQuestion) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(surveyQuestionLabel(question))
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            ForEach(question.options, id: \.self) { option in
                HStack {
                    Text(option.lowercased())
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.foreground)
                    Spacer()
                    ForEach(["yes", "maybe"], id: \.self) { choice in
                        let on = model.mapAnswer(question.id)[option] == choice
                        PDAButton(choice, variant: on ? .primary : .secondary) {
                            var next = model.mapAnswer(question.id)
                            if next[option] == choice { next[option] = nil } else { next[option] = choice }
                            model.setMap(question.id, next)
                        }
                        .disabled(model.readOnly)
                    }
                }
                .padding(12)
                .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.md))
                .overlay {
                    RoundedRectangle(cornerRadius: PDARadius.md)
                        .strokeBorder(PDAColor.border, lineWidth: 1)
                }
            }
        }
    }

    private func textBinding(_ model: SurveyPageModel, _ id: String) -> Binding<String> {
        Binding(get: { model.textAnswer(id) }, set: { model.setText(id, $0) })
    }
}

private func surveyQuestionLabel(_ question: PublicSurveyQuestion) -> String {
    let label = question.label.lowercased()
    return question.required ? label : "\(label) (optional)"
}
