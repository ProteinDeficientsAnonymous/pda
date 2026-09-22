import SwiftUI

enum AdminJoinFormCopy {
    static let title = "join form"
    static let subtitle = "questions shown to applicants on /join. name + phone are always included."
    static let loading = "loading…"
    static let error = "couldn't load questions — try refreshing"
    static let empty = "no custom questions yet"
    static let forbiddenTitle = "join form"
    static let forbiddenBody = "you need permission to edit join questions to see this list."
}

enum AdminJoinFormError: Error, Equatable {
    case forbidden
}

enum DeleteQuestionCopy {
    static let button = "delete"
    static let title = "delete question"
    static let confirm = "delete"
    static let cancel = "cancel"
    static let failure = "couldn't delete the question — try again"
    static let forbiddenTitle = "delete question"
    static let forbiddenBody = "you need permission to edit join questions to delete this question."
}

struct DeleteQuestionPrompt: Equatable {
    let title: String
    let message: String
    let confirmLabel: String
}

enum DeleteQuestionError: Error {
    case forbidden
}

func joinQuestionDeleteMessage(_ question: JoinQuestion) -> String {
    "delete \"\(question.label)\"?"
}

func adminJoinQuestionsURL(base: URL) -> URL {
    joinFormURL(base: base)
}

func adminJoinQuestionTitle(_ question: JoinQuestion) -> String {
    let label = question.label.lowercased()
    return question.required ? "\(label) · required" : label
}

func adminJoinQuestionDetail(_ question: JoinQuestion) -> String {
    let type = question.fieldType.lowercased()
    guard type == "select", !question.options.isEmpty else { return type }
    return "\(type) · \(question.options.count) options"
}

extension EventsClient {
    func adminJoinQuestions() async throws -> [JoinQuestion] {
        var req = URLRequest(url: adminJoinQuestionsURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw AdminJoinFormError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([JoinQuestion].self, from: data)
            .sorted { $0.displayOrder < $1.displayOrder }
    }

    func deleteJoinQuestion(id: String) async throws {
        var req = URLRequest(url: updateJoinQuestionURL(base: baseURL, id: id))
        req.httpMethod = "DELETE"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (_, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw DeleteQuestionError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
    }
}

@Observable
final class AdminJoinFormModel {
    var client: EventsClient
    var questions: [JoinQuestion] = []
    var forbidden = false
    var error: String?
    var loaded = false
    var pendingDelete: JoinQuestion?
    var deleteError: String?
    var deleteForbidden = false

    var explanationTitle: String { AdminJoinFormCopy.forbiddenTitle }
    var explanationBody: String { AdminJoinFormCopy.forbiddenBody }
    var deleteExplanationTitle: String { DeleteQuestionCopy.forbiddenTitle }
    var deleteExplanationBody: String { DeleteQuestionCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            questions = try await client.adminJoinQuestions()
            loaded = true
        } catch AdminJoinFormError.forbidden {
            questions = []
            forbidden = true
            loaded = true
        } catch {
            questions = []
            self.error = AdminJoinFormCopy.error
            loaded = true
        }
    }

    func prepareDelete(_ question: JoinQuestion) -> DeleteQuestionPrompt? {
        pendingDelete = question
        return DeleteQuestionPrompt(
            title: DeleteQuestionCopy.title,
            message: joinQuestionDeleteMessage(question),
            confirmLabel: DeleteQuestionCopy.confirm
        )
    }

    func cancelDelete() {
        pendingDelete = nil
    }

    func commitDelete() async -> Bool {
        guard let question = pendingDelete else { return false }
        return await commitDelete(question)
    }

    func commitDelete(_ question: JoinQuestion) async -> Bool {
        pendingDelete = nil
        deleteError = nil
        deleteForbidden = false
        do {
            try await client.deleteJoinQuestion(id: question.id)
            questions.removeAll { $0.id == question.id }
            return true
        } catch DeleteQuestionError.forbidden {
            deleteForbidden = true
            return false
        } catch {
            deleteError = DeleteQuestionCopy.failure
            return false
        }
    }
}

struct AdminJoinFormView: View {
    var client: EventsClient
    @State private var model: AdminJoinFormModel?
    @State private var addingQuestion = false
    @State private var editingQuestion: JoinQuestion?

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
                VStack(alignment: .leading, spacing: 8) {
                    HStack {
                        Spacer()
                        Button(AddQuestionCopy.button) { addingQuestion = true }
                    }
                    .padding(.horizontal)
                    Text(AdminJoinFormCopy.subtitle)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal)
                    if model.deleteForbidden {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(model.deleteExplanationTitle).font(.headline)
                            Text(model.deleteExplanationBody).foregroundStyle(.secondary)
                        }
                        .padding(.horizontal)
                    }
                    if let deleteError = model.deleteError {
                        Text(deleteError).font(.footnote).foregroundStyle(.red).padding(.horizontal)
                    }
                    if model.questions.isEmpty {
                        ContentUnavailableView(AdminJoinFormCopy.empty, systemImage: "questionmark")
                    } else {
                        List(model.questions) { question in
                            HStack {
                                VStack(alignment: .leading, spacing: 2) {
                                    Text(adminJoinQuestionTitle(question))
                                    Text(adminJoinQuestionDetail(question))
                                        .font(.footnote)
                                        .foregroundStyle(.secondary)
                                }
                                Spacer()
                                Button(AddQuestionCopy.edit) { editingQuestion = question }
                                Button(DeleteQuestionCopy.button, role: .destructive) {
                                    _ = model.prepareDelete(question)
                                }
                            }
                        }
                    }
                }
            } else {
                ProgressView(AdminJoinFormCopy.loading)
            }
        }
        .navigationTitle(AdminJoinFormCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $addingQuestion) {
            NavigationStack {
                AddQuestionView(client: client) { question in
                    model?.includeCreated(question)
                }
            }
        }
        .sheet(item: $editingQuestion) { question in
            NavigationStack {
                AddQuestionView(client: client, question: question) { updated in
                    model?.replaceUpdated(updated)
                }
            }
        }
        .confirmationDialog(
            DeleteQuestionCopy.title,
            isPresented: Binding(
                get: { model?.pendingDelete != nil },
                set: { if !$0 { model?.cancelDelete() } }
            ),
            titleVisibility: .visible
        ) {
            Button(DeleteQuestionCopy.confirm, role: .destructive) {
                guard let question = model?.pendingDelete else { return }
                Task { _ = await model?.commitDelete(question) }
            }
            Button(DeleteQuestionCopy.cancel, role: .cancel) {
                model?.cancelDelete()
            }
        } message: {
            if let question = model?.pendingDelete {
                Text(joinQuestionDeleteMessage(question))
            }
        }
        .task {
            if model == nil { model = AdminJoinFormModel(client: client) }
            await model?.load()
        }
    }
}
