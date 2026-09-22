import SwiftUI

enum AddSurveyQuestionCopy {
    static let button = "add question"
    static let edit = "edit"
    static let title = "add question"
    static let editTitle = "edit question"
    static let questions = "questions"
    static let empty = "no questions yet"
    static let loadError = "couldn't load survey — try refreshing"
    static let label = "label"
    static let type = "type"
    static let options = "options"
    static let addOption = "+ add option"
    static let remove = "remove"
    static let required = "required"
    static let cancel = "cancel"
    static let save = "save"
    static let saving = "saving…"
    static let labelRequired = "label required"
    static let optionsRequired = "add at least one option"
    static let failure = "couldn't save — try again"
    static let forbidden = "you don't have permission to do that"
    static let notFound = "survey not found"
    static let questionNotFound = "question not found"
    static let ratingHint = "up to 5 star labels"
    static let pollHint = "iso-8601 datetime values"
}

struct SurveyQuestionTypeChoice: Equatable, Identifiable {
    var id: String { value }
    let value: String
    let label: String
    let wantsOptions: Bool
}

let surveyQuestionTypeChoices: [SurveyQuestionTypeChoice] = [
    SurveyQuestionTypeChoice(value: "text", label: "short text", wantsOptions: false),
    SurveyQuestionTypeChoice(value: "textarea", label: "short answer", wantsOptions: false),
    SurveyQuestionTypeChoice(value: "radio", label: "radio", wantsOptions: true),
    SurveyQuestionTypeChoice(value: "select", label: "select", wantsOptions: true),
    SurveyQuestionTypeChoice(value: "checkbox", label: "checkbox", wantsOptions: true),
    SurveyQuestionTypeChoice(value: "number", label: "number", wantsOptions: false),
    SurveyQuestionTypeChoice(value: "boolean", label: "yes / no", wantsOptions: false),
    SurveyQuestionTypeChoice(value: "rating", label: "1–5 rating", wantsOptions: true),
    SurveyQuestionTypeChoice(value: "datetime_poll", label: "datetime poll (iso options)", wantsOptions: true),
]

enum DeleteSurveyQuestionCopy {
    static let title = "delete question"
    static let confirm = "delete"
    static let cancel = "cancel"
}

enum ReorderSurveyQuestionsCopy {
    static let moveUp = "move up"
    static let moveDown = "move down"
}

func showsSurveyQuestionMoveUp(index: Int, count: Int) -> Bool {
    count > 1 && index > 0
}

func showsSurveyQuestionMoveDown(index: Int, count: Int) -> Bool {
    count > 1 && index < count - 1
}

func surveyQuestionDeleteMessage(_ label: String) -> String {
    "delete \"\(label)\"? this also deletes responses to it."
}

enum AddSurveyQuestionError: Error, Equatable {
    case forbidden
    case notFound
    case questionNotFound
    case failed
}

struct AdminSurveyDetail: Decodable, Equatable {
    let id: String
    let title: String
    let slug: String
    let visibility: String
    let questions: [PublicSurveyQuestion]

    init(id: String, title: String, slug: String, visibility: String, questions: [PublicSurveyQuestion]) {
        self.id = id
        self.title = title
        self.slug = slug
        self.visibility = visibility
        self.questions = questions.sorted { $0.displayOrder < $1.displayOrder }
    }

    enum CodingKeys: String, CodingKey {
        case id, title, slug, visibility, questions
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        title = try c.decodeIfPresent(String.self, forKey: .title) ?? ""
        slug = try c.decodeIfPresent(String.self, forKey: .slug) ?? ""
        visibility = try c.decodeIfPresent(String.self, forKey: .visibility) ?? ""
        questions = (try c.decodeIfPresent([PublicSurveyQuestion].self, forKey: .questions) ?? [])
            .sorted { $0.displayOrder < $1.displayOrder }
    }
}

func surveyQuestionWantsOptions(_ fieldType: String) -> Bool {
    surveyQuestionTypeChoices.first { $0.value == fieldType }?.wantsOptions == true
}

func surveyQuestionOptions(_ raw: [String]) -> [String] {
    raw.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
}

func surveyQuestionOptionsHint(_ fieldType: String) -> String? {
    switch fieldType {
    case "rating": AddSurveyQuestionCopy.ratingHint
    case "datetime_poll": AddSurveyQuestionCopy.pollHint
    default: nil
    }
}

func clampedSurveyQuestionLabel(_ value: String) -> String { String(value.prefix(200)) }

func adminSurveyQuestionLabel(_ question: PublicSurveyQuestion) -> String {
    let label = question.label.lowercased()
    return question.required ? "\(label) · required" : label
}

func adminSurveyQuestionMeta(_ question: PublicSurveyQuestion) -> String {
    question.options.isEmpty
        ? question.fieldType
        : "\(question.fieldType) · \(question.options.count) options"
}

func adminSurveyURL(base: URL, surveyId: String) -> URL {
    let encoded = surveyId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? surveyId
    return URL(string: "/api/community/surveys/\(encoded)/admin/", relativeTo: base)!.absoluteURL
}

func addSurveyQuestionURL(base: URL, surveyId: String) -> URL {
    let encoded = surveyId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? surveyId
    return URL(string: "/api/community/surveys/\(encoded)/questions/", relativeTo: base)!.absoluteURL
}

func reorderSurveyQuestionsURL(base: URL, surveyId: String) -> URL {
    let encoded = surveyId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? surveyId
    return URL(string: "/api/community/surveys/\(encoded)/questions/order/", relativeTo: base)!.absoluteURL
}

func updateSurveyQuestionURL(base: URL, surveyId: String, questionId: String) -> URL {
    let survey = surveyId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? surveyId
    let question = questionId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) ?? questionId
    return URL(string: "/api/community/surveys/\(survey)/questions/\(question)/", relativeTo: base)!.absoluteURL
}

func addSurveyQuestionError(data: Data) -> AddSurveyQuestionError {
    switch apiErrorCode(from: data) {
    case "perm.denied": .forbidden
    case "survey.not_found": .notFound
    case "survey.question_not_found": .questionNotFound
    default: .failed
    }
}

extension EventsClient {
    func adminSurvey(id: String) async throws -> AdminSurveyDetail {
        var req = URLRequest(url: adminSurveyURL(base: baseURL, surveyId: id))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(AdminSurveyDetail.self, from: data)
    }

    func createSurveyQuestion(
        surveyId: String,
        label: String,
        fieldType: String,
        options: [String],
        required: Bool
    ) async throws -> PublicSurveyQuestion {
        var req = URLRequest(url: addSurveyQuestionURL(base: baseURL, surveyId: surveyId))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "label": label,
            "field_type": fieldType,
            "options": options,
            "required": required,
        ])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw addSurveyQuestionError(data: data) }
        return try Event.decoder.decode(PublicSurveyQuestion.self, from: data)
    }

    func updateSurveyQuestion(
        surveyId: String,
        questionId: String,
        label: String,
        fieldType: String,
        options: [String],
        required: Bool
    ) async throws -> PublicSurveyQuestion {
        var req = URLRequest(url: updateSurveyQuestionURL(base: baseURL, surveyId: surveyId, questionId: questionId))
        req.httpMethod = "PATCH"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: [
            "label": label,
            "field_type": fieldType,
            "options": options,
            "required": required,
        ])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw addSurveyQuestionError(data: data) }
        return try Event.decoder.decode(PublicSurveyQuestion.self, from: data)
    }

    func deleteSurveyQuestion(surveyId: String, questionId: String) async throws {
        var req = URLRequest(url: updateSurveyQuestionURL(base: baseURL, surveyId: surveyId, questionId: questionId))
        req.httpMethod = "DELETE"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw addSurveyQuestionError(data: data) }
    }

    func reorderSurveyQuestions(surveyId: String, ids: [String]) async throws -> [PublicSurveyQuestion] {
        var req = URLRequest(url: reorderSurveyQuestionsURL(base: baseURL, surveyId: surveyId))
        req.httpMethod = "PUT"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.httpBody = try JSONSerialization.data(withJSONObject: ["question_ids": ids])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw addSurveyQuestionError(data: data) }
        return try Event.decoder.decode([PublicSurveyQuestion].self, from: data)
    }
}

@Observable
final class SurveyQuestionsModel {
    var client: EventsClient
    var surveyId: String
    var survey: AdminSurveyDetail?
    var error: String?
    var actionError: String?
    var pendingDelete: PublicSurveyQuestion?
    var loaded = false

    init(client: EventsClient, surveyId: String) {
        self.client = client
        self.surveyId = surveyId
    }

    func load() async {
        do {
            survey = try await client.adminSurvey(id: surveyId)
            error = nil
            loaded = true
        } catch {
            survey = nil
            self.error = AddSurveyQuestionCopy.loadError
            loaded = true
        }
    }

    func cancelDelete() {
        pendingDelete = nil
    }

    func commitDelete() async {
        guard let question = pendingDelete else { return }
        await commitDelete(question)
    }

    func commitDelete(_ question: PublicSurveyQuestion) async {
        pendingDelete = nil
        do {
            try await client.deleteSurveyQuestion(surveyId: surveyId, questionId: question.id)
            actionError = nil
            await load()
        } catch AddSurveyQuestionError.forbidden {
            actionError = AddSurveyQuestionCopy.forbidden
        } catch AddSurveyQuestionError.questionNotFound {
            actionError = AddSurveyQuestionCopy.questionNotFound
        } catch {
            return
        }
    }

    func moveUp(at index: Int) async {
        await reorder(from: index, to: index - 1)
    }

    func moveDown(at index: Int) async {
        await reorder(from: index, to: index + 1)
    }

    private func reorder(from: Int, to: Int) async {
        guard let current = survey else { return }
        let questions = current.questions
        guard questions.indices.contains(from), questions.indices.contains(to) else { return }
        var ids = questions.map(\.id)
        ids.swapAt(from, to)
        do {
            let next = try await client.reorderSurveyQuestions(surveyId: surveyId, ids: ids)
            actionError = nil
            survey = AdminSurveyDetail(
                id: current.id,
                title: current.title,
                slug: current.slug,
                visibility: current.visibility,
                questions: next
            )
        } catch AddSurveyQuestionError.forbidden {
            actionError = AddSurveyQuestionCopy.forbidden
        } catch AddSurveyQuestionError.notFound {
            actionError = AddSurveyQuestionCopy.notFound
        } catch {
            return
        }
    }
}

@Observable
final class AddSurveyQuestionModel {
    var client: EventsClient
    var surveyId: String
    var label = ""
    var fieldType = "text"
    var required = false
    var options: [String] = [""]
    var question: PublicSurveyQuestion?
    var banner: String?
    var busy = false
    var created: PublicSurveyQuestion?

    init(client: EventsClient, surveyId: String, question: PublicSurveyQuestion? = nil) {
        self.client = client
        self.surveyId = surveyId
        self.question = question
        if let question {
            label = question.label
            fieldType = question.fieldType
            required = question.required
            options = question.options.isEmpty ? [""] : question.options
        }
    }

    var title: String { question == nil ? AddSurveyQuestionCopy.title : AddSurveyQuestionCopy.editTitle }
    var showsOptions: Bool { surveyQuestionWantsOptions(fieldType) }
    var optionsHint: String? { surveyQuestionOptionsHint(fieldType) }

    func setFieldType(_ value: String) {
        fieldType = value
        let blank = options.allSatisfy { $0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        if surveyQuestionWantsOptions(value), blank {
            options = [""]
        }
    }

    func save() async {
        banner = nil
        let trimmed = label.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            banner = AddSurveyQuestionCopy.labelRequired
            return
        }
        let normalized = showsOptions ? surveyQuestionOptions(options) : []
        if showsOptions, normalized.isEmpty {
            banner = AddSurveyQuestionCopy.optionsRequired
            return
        }
        busy = true
        defer { busy = false }
        do {
            if let question {
                created = try await client.updateSurveyQuestion(
                    surveyId: surveyId,
                    questionId: question.id,
                    label: trimmed,
                    fieldType: fieldType,
                    options: normalized,
                    required: required
                )
            } else {
                created = try await client.createSurveyQuestion(
                    surveyId: surveyId,
                    label: trimmed,
                    fieldType: fieldType,
                    options: normalized,
                    required: required
                )
            }
        } catch AddSurveyQuestionError.forbidden {
            banner = AddSurveyQuestionCopy.forbidden
        } catch AddSurveyQuestionError.notFound {
            banner = AddSurveyQuestionCopy.notFound
        } catch AddSurveyQuestionError.questionNotFound {
            banner = AddSurveyQuestionCopy.questionNotFound
        } catch {
            banner = AddSurveyQuestionCopy.failure
        }
    }
}

struct SurveyQuestionsView: View {
    let surveyId: String
    var client: EventsClient
    @State private var model: SurveyQuestionsModel?
    @State private var showAdd = false
    @State private var editing: PublicSurveyQuestion?

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
                        Text("/\(survey.slug) · \(survey.visibility)")
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.muted)
                        HStack {
                            Text(AddSurveyQuestionCopy.questions)
                                .font(PDAType.field)
                                .fontWeight(.medium)
                            Spacer()
                            PDAButton(AddSurveyQuestionCopy.button) { showAdd = true }
                        }
                        if let actionError = model.actionError {
                            Text(actionError)
                                .font(PDAType.control)
                                .foregroundStyle(PDAColor.destructive)
                        }
                        if survey.questions.isEmpty {
                            Text(AddSurveyQuestionCopy.empty)
                                .font(PDAType.control)
                                .foregroundStyle(PDAColor.muted)
                        } else {
                            ForEach(Array(survey.questions.enumerated()), id: \.element.id) { index, question in
                                questionRow(question, index: index, count: survey.questions.count)
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
        .navigationTitle((model?.survey?.title ?? AddSurveyQuestionCopy.questions).lowercased())
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $showAdd) {
            AddSurveyQuestionSheet(client: client, surveyId: surveyId) {
                showAdd = false
                Task { await model?.load() }
            }
        }
        .sheet(item: $editing) { question in
            AddSurveyQuestionSheet(client: client, surveyId: surveyId, question: question) {
                editing = nil
                Task { await model?.load() }
            }
        }
        .confirmationDialog(
            DeleteSurveyQuestionCopy.title,
            isPresented: Binding(
                get: { model?.pendingDelete != nil },
                set: { if !$0 { model?.cancelDelete() } }
            ),
            titleVisibility: .visible,
            presenting: model?.pendingDelete
        ) { question in
            Button(DeleteSurveyQuestionCopy.confirm, role: .destructive) {
                Task { await model?.commitDelete(question) }
            }
            Button(DeleteSurveyQuestionCopy.cancel, role: .cancel) {}
        } message: { question in
            Text(surveyQuestionDeleteMessage(question.label))
        }
        .task {
            if model == nil { model = SurveyQuestionsModel(client: client, surveyId: surveyId) }
            await model?.load()
        }
    }

    private func questionRow(_ question: PublicSurveyQuestion, index: Int, count: Int) -> some View {
        HStack(alignment: .center, spacing: 8) {
            VStack(alignment: .leading, spacing: 4) {
                Text(adminSurveyQuestionLabel(question))
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foreground)
                Text(adminSurveyQuestionMeta(question))
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.muted)
            }
            Spacer()
            if showsSurveyQuestionMoveUp(index: index, count: count) {
                PDAButton(ReorderSurveyQuestionsCopy.moveUp, variant: .ghost) {
                    Task { await model?.moveUp(at: index) }
                }
            }
            if showsSurveyQuestionMoveDown(index: index, count: count) {
                PDAButton(ReorderSurveyQuestionsCopy.moveDown, variant: .ghost) {
                    Task { await model?.moveDown(at: index) }
                }
            }
            PDAButton(AddSurveyQuestionCopy.edit, variant: .ghost) { editing = question }
            PDAButton(DeleteSurveyQuestionCopy.confirm, variant: .ghost) { model?.pendingDelete = question }
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

struct AddSurveyQuestionSheet: View {
    var onCreated: () -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var model: AddSurveyQuestionModel

    init(client: EventsClient, surveyId: String, question: PublicSurveyQuestion? = nil, onCreated: @escaping () -> Void) {
        self.onCreated = onCreated
        _model = State(initialValue: AddSurveyQuestionModel(client: client, surveyId: surveyId, question: question))
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    PDATextField(AddSurveyQuestionCopy.label, text: labelText)
                    VStack(alignment: .leading, spacing: 4) {
                        Text(AddSurveyQuestionCopy.type)
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.foreground)
                        Picker(AddSurveyQuestionCopy.type, selection: fieldType) {
                            ForEach(surveyQuestionTypeChoices) { choice in
                                Text(choice.label).tag(choice.value)
                            }
                        }
                        .pickerStyle(.menu)
                        .font(PDAType.field)
                    }
                    if model.showsOptions {
                        Text(AddSurveyQuestionCopy.options)
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.foreground)
                        if let hint = model.optionsHint {
                            Text(hint)
                                .font(PDAType.control)
                                .foregroundStyle(PDAColor.foregroundTertiary)
                        }
                        ForEach(model.options.indices, id: \.self) { index in
                            HStack(alignment: .bottom) {
                                PDATextField("option \(index + 1)", text: optionText(index))
                                PDAButton(AddSurveyQuestionCopy.remove, variant: .ghost) {
                                    model.options.remove(at: index)
                                }
                                .accessibilityLabel("remove option \(index + 1)")
                            }
                        }
                        PDAButton(AddSurveyQuestionCopy.addOption, variant: .secondary) {
                            model.options.append("")
                        }
                    }
                    Toggle(AddSurveyQuestionCopy.required, isOn: required)
                        .font(PDAType.field)
                        .foregroundStyle(PDAColor.foreground)
                    if let banner = model.banner {
                        Text(banner).font(PDAType.control).foregroundStyle(PDAColor.destructive)
                    }
                    HStack {
                        Spacer()
                        PDAButton(AddSurveyQuestionCopy.cancel, variant: .ghost) { dismiss() }
                            .disabled(model.busy)
                        PDAButton(model.busy ? AddSurveyQuestionCopy.saving : AddSurveyQuestionCopy.save) {
                            Task { await model.save() }
                        }
                        .disabled(model.busy)
                    }
                }
                .padding()
            }
            .background(PDAColor.background)
            .navigationTitle(model.title)
            .navigationBarTitleDisplayMode(.inline)
        }
        .onChange(of: model.created?.id) { _, id in
            if id != nil { onCreated() }
        }
    }

    private var labelText: Binding<String> {
        Binding(
            get: { model.label },
            set: { model.label = clampedSurveyQuestionLabel($0) }
        )
    }

    private var fieldType: Binding<String> {
        Binding(get: { model.fieldType }, set: { model.setFieldType($0) })
    }

    private var required: Binding<Bool> {
        Binding(get: { model.required }, set: { model.required = $0 })
    }

    private func optionText(_ index: Int) -> Binding<String> {
        Binding(
            get: { model.options.indices.contains(index) ? model.options[index] : "" },
            set: { value in
                guard model.options.indices.contains(index) else { return }
                model.options[index] = value
            }
        )
    }
}
