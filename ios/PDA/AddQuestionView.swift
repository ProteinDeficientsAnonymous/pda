import SwiftUI

enum AddQuestionCopy {
    static let button = "add question"
    static let title = "add question"
    static let labelField = "label"
    static let type = "type"
    static let required = "required"
    static let options = "options"
    static let addOption = "+ add option"
    static let remove = "remove"
    static let save = "save"
    static let saving = "saving…"
    static let cancel = "cancel"
    static let labelRequired = "label required"
    static let optionsRequired = "add at least one option"
    static let failure = "couldn't save — try again"
    static let forbiddenTitle = "add question"
    static let forbiddenBody = "you need permission to edit join questions to add a question."
}

struct JoinQuestionTypeChoice: Equatable {
    let value: String
    let label: String
}

let joinQuestionTypeChoices: [JoinQuestionTypeChoice] = [
    JoinQuestionTypeChoice(value: "text", label: "short text"),
    JoinQuestionTypeChoice(value: "textarea", label: "short answer"),
    JoinQuestionTypeChoice(value: "select", label: "select"),
]

func joinQuestionOptions(_ raw: [String]) -> [String] {
    raw.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
}

func joinQuestionPayloadOptions(fieldType: String, options: [String]) -> [String] {
    fieldType == "select" ? joinQuestionOptions(options) : []
}

func addQuestionURL(base: URL) -> URL {
    URL(string: "/api/community/join-form/questions/", relativeTo: base)!.absoluteURL
}

enum AddQuestionError: Error, Equatable {
    case forbidden
}

extension EventsClient {
    func createJoinQuestion(
        label: String,
        fieldType: String,
        options: [String],
        required: Bool
    ) async throws -> JoinQuestion {
        var req = URLRequest(url: addQuestionURL(base: baseURL))
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
        if status == 403 { throw AddQuestionError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(JoinQuestion.self, from: data)
    }
}

@Observable
final class AddQuestionModel {
    var client: EventsClient
    var label = ""
    var fieldType = "text"
    var required = false
    var options: [String] = [""]
    var formError: String?
    var forbidden = false
    var saving = false
    var closed = false
    var created: JoinQuestion?

    var showsOptions: Bool { fieldType == "select" }
    var saveLabel: String { saving ? AddQuestionCopy.saving : AddQuestionCopy.save }
    var canSave: Bool { !saving && !forbidden }
    var explanationTitle: String { AddQuestionCopy.forbiddenTitle }
    var explanationBody: String { AddQuestionCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func save() async -> Bool {
        let trimmed = label.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            formError = AddQuestionCopy.labelRequired
            return false
        }
        let payloadOptions = joinQuestionPayloadOptions(fieldType: fieldType, options: options)
        if fieldType == "select", payloadOptions.isEmpty {
            formError = AddQuestionCopy.optionsRequired
            return false
        }
        formError = nil
        saving = true
        defer { saving = false }
        do {
            created = try await client.createJoinQuestion(
                label: trimmed,
                fieldType: fieldType,
                options: payloadOptions,
                required: required
            )
            closed = true
            return true
        } catch AddQuestionError.forbidden {
            forbidden = true
            return false
        } catch {
            formError = AddQuestionCopy.failure
            return false
        }
    }

    func cancel() {
        closed = true
    }
}

extension AdminJoinFormModel {
    func includeCreated(_ question: JoinQuestion) {
        questions.append(question)
        questions.sort { $0.displayOrder < $1.displayOrder }
    }
}

struct AddQuestionView: View {
    var client: EventsClient
    var onCreated: (JoinQuestion) -> Void = { _ in }
    @Environment(\.dismiss) private var dismiss
    @State private var model: AddQuestionModel?

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
            } else if let model {
                Form {
                    TextField(AddQuestionCopy.labelField, text: labelBinding(model))
                        .textInputAutocapitalization(.never)
                    Picker(AddQuestionCopy.type, selection: typeBinding(model)) {
                        ForEach(joinQuestionTypeChoices, id: \.value) { choice in
                            Text(choice.label).tag(choice.value)
                        }
                    }
                    if model.showsOptions {
                        Section(AddQuestionCopy.options) {
                            ForEach(model.options.indices, id: \.self) { index in
                                HStack {
                                    TextField("option \(index + 1)", text: optionBinding(model, index))
                                        .textInputAutocapitalization(.never)
                                    Button(AddQuestionCopy.remove) {
                                        model.options.remove(at: index)
                                    }
                                }
                            }
                            Button(AddQuestionCopy.addOption) { model.options.append("") }
                        }
                    }
                    Toggle(AddQuestionCopy.required, isOn: requiredBinding(model))
                    if let formError = model.formError {
                        Text(formError).foregroundStyle(.red)
                    }
                }
            }
        }
        .navigationTitle(AddQuestionCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .cancellationAction) {
                Button(AddQuestionCopy.cancel) {
                    model?.cancel()
                    dismiss()
                }
            }
            if model?.forbidden != true {
                ToolbarItem(placement: .confirmationAction) {
                    Button(model?.saveLabel ?? AddQuestionCopy.save) {
                        Task { await submit() }
                    }
                    .disabled(model?.canSave != true)
                }
            }
        }
        .task {
            if model == nil { model = AddQuestionModel(client: client) }
        }
    }

    private func labelBinding(_ model: AddQuestionModel) -> Binding<String> {
        Binding(get: { model.label }, set: { model.label = $0 })
    }

    private func typeBinding(_ model: AddQuestionModel) -> Binding<String> {
        Binding(get: { model.fieldType }, set: { model.fieldType = $0 })
    }

    private func requiredBinding(_ model: AddQuestionModel) -> Binding<Bool> {
        Binding(get: { model.required }, set: { model.required = $0 })
    }

    private func optionBinding(_ model: AddQuestionModel, _ index: Int) -> Binding<String> {
        Binding(
            get: { model.options.indices.contains(index) ? model.options[index] : "" },
            set: { if model.options.indices.contains(index) { model.options[index] = $0 } }
        )
    }

    private func submit() async {
        guard let model, await model.save(), let created = model.created else { return }
        onCreated(created)
        dismiss()
    }
}
