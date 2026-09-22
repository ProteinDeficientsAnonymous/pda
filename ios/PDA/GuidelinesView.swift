import SwiftUI

enum GuidelinesCopy {
    static let title = "community guidelines"
    static let loading = "loading…"
    static let error = "couldn't load the guidelines — try refreshing"
}

enum GuidelinesEditorCopy {
    static let edit = "edit"
    static let done = "done"
    static let placeholder = "guidelines content"
    static let saving = "saving…"
    static let saved = "saved ✓"
    static let saveError = "couldn't save"
}

enum GuidelinesAutosaveStatus: Equatable {
    case idle, saving, saved, error
}

func showsGuidelinesEdit(_ user: SessionUser?) -> Bool {
    guard let user else { return false }
    return user.isAdmin || user.permissions.contains("edit_guidelines")
}

func guidelinesAutosaveLabel(_ status: GuidelinesAutosaveStatus) -> String? {
    switch status {
    case .idle: nil
    case .saving: GuidelinesEditorCopy.saving
    case .saved: GuidelinesEditorCopy.saved
    case .error: GuidelinesEditorCopy.saveError
    }
}

func guidelinesURL(base: URL) -> URL {
    URL(string: "/api/community/guidelines/", relativeTo: base)!.absoluteURL
}

@Observable
final class GuidelinesEditorModel {
    var client: EventsClient
    var user: SessionUser?
    var page: HomePage?
    var editing = false
    var draft = ""
    var status: GuidelinesAutosaveStatus = .idle
    var error: String?
    var autosaveDelay: Duration = .seconds(2)

    var canEdit: Bool { showsGuidelinesEdit(user) }

    private var saveTask: Task<Void, Never>?
    private var pending: String?
    private var saving: Task<Void, Never>?
    private var savingValue: String?
    private var savedTask: Task<Void, Never>?
    private let savedBadge: Duration = .seconds(2)

    init(client: EventsClient = EventsClient(), user: SessionUser? = nil) {
        self.client = client
        self.user = user
    }

    func load() async {
        error = nil
        do {
            page = try await client.guidelines()
        } catch {
            page = nil
            self.error = GuidelinesCopy.error
        }
    }

    func beginEdit() {
        guard canEdit, let page else { return }
        draft = page.contentPm
        status = .idle
        editing = true
    }

    func change(_ next: String) {
        guard editing else { return }
        draft = next
        schedule(next)
    }

    func done() async {
        saveTask?.cancel()
        saveTask = nil
        pending = nil
        if draft != (page?.contentPm ?? "") {
            await performSave(draft)
        }
        editing = false
    }

    private func schedule(_ value: String) {
        saveTask?.cancel()
        pending = value
        let delay = autosaveDelay
        saveTask = Task { [weak self] in
            try? await Task.sleep(for: delay)
            guard let self, !Task.isCancelled, self.pending == value else { return }
            self.pending = nil
            await self.performSave(value)
        }
    }

    private func performSave(_ value: String) async {
        if let saving, savingValue == value {
            await saving.value
            return
        }
        savingValue = value
        let task = Task { [weak self] in
            guard let self else { return }
            self.status = .saving
            self.savedTask?.cancel()
            do {
                let page = try await self.client.updateGuidelines(contentPm: value)
                self.page = page
                self.status = .saved
                self.savedTask = Task { [weak self] in
                    try? await Task.sleep(for: self?.savedBadge ?? .seconds(2))
                    guard let self, !Task.isCancelled, self.status == .saved else { return }
                    self.status = .idle
                }
            } catch {
                self.status = .error
            }
        }
        saving = task
        await task.value
        if savingValue == value {
            saving = nil
            savingValue = nil
        }
    }
}

struct GuidelinesView: View {
    var client = EventsClient()
    var user: SessionUser?
    @Environment(\.dismiss) private var dismiss
    @State private var model: GuidelinesEditorModel?

    var body: some View {
        NavigationStack {
            Group {
                if let model, let error = model.error {
                    ContentUnavailableView {
                        Label(error, systemImage: "exclamationmark.triangle")
                    } actions: {
                        PDAButton("try again") { Task { await model.load() } }
                    }
                } else if let model, model.page != nil {
                    editor(model)
                } else {
                    ProgressView(GuidelinesCopy.loading)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(PDAColor.background)
            .navigationTitle(GuidelinesCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton("close", variant: .secondary) { dismiss() }
                }
            }
            .task {
                if model == nil { model = GuidelinesEditorModel(client: client, user: user) }
                await model?.load()
            }
        }
    }

    @ViewBuilder
    private func editor(_ model: GuidelinesEditorModel) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            if model.editing {
                HStack(spacing: 8) {
                    if let label = guidelinesAutosaveLabel(model.status) {
                        Text(label)
                            .font(PDAType.control)
                            .foregroundStyle(autosaveColor(model.status))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(autosaveFill(model.status), in: Capsule())
                    }
                    Spacer(minLength: 0)
                    PDAButton(GuidelinesEditorCopy.done, variant: .ghost) {
                        Task { await model.done() }
                    }
                }
                .padding(.horizontal)
                PDATextField(
                    GuidelinesEditorCopy.placeholder,
                    text: Binding(get: { model.draft }, set: { model.change($0) }),
                    axis: .vertical,
                    capitalization: .never,
                    disableAutocorrection: true,
                    lineLimit: 8
                )
                .padding(.horizontal)
            } else {
                if model.canEdit {
                    HStack {
                        Spacer(minLength: 0)
                        PDAButton(GuidelinesEditorCopy.edit, variant: .ghost) { model.beginEdit() }
                    }
                    .padding(.horizontal)
                }
                if let html = model.page?.contentHtml {
                    ContentHTMLView(html: html, baseURL: client.baseURL)
                }
            }
        }
    }

    private func autosaveColor(_ status: GuidelinesAutosaveStatus) -> Color {
        switch status {
        case .saved: PDAColor.success
        case .error: PDAColor.destructive
        case .saving, .idle: PDAColor.foregroundTertiary
        }
    }

    private func autosaveFill(_ status: GuidelinesAutosaveStatus) -> Color {
        switch status {
        case .saved: PDAColor.successSubtle
        case .error: PDAColor.destructiveSubtle
        case .saving, .idle: PDAColor.surfaceDim
        }
    }
}
