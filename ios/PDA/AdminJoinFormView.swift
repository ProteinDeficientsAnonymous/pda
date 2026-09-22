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
}

@Observable
final class AdminJoinFormModel {
    var client: EventsClient
    var questions: [JoinQuestion] = []
    var forbidden = false
    var error: String?
    var loaded = false

    var explanationTitle: String { AdminJoinFormCopy.forbiddenTitle }
    var explanationBody: String { AdminJoinFormCopy.forbiddenBody }

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
}

struct AdminJoinFormView: View {
    var client: EventsClient
    @State private var model: AdminJoinFormModel?

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
                    Text(AdminJoinFormCopy.subtitle)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .padding(.horizontal)
                    if model.questions.isEmpty {
                        ContentUnavailableView(AdminJoinFormCopy.empty, systemImage: "questionmark")
                    } else {
                        List(model.questions) { question in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(adminJoinQuestionTitle(question))
                                Text(adminJoinQuestionDetail(question))
                                    .font(.footnote)
                                    .foregroundStyle(.secondary)
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
        .task {
            if model == nil { model = AdminJoinFormModel(client: client) }
            await model?.load()
        }
    }
}
