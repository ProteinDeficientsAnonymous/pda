import SwiftUI
import WebKit

enum HomeCopy {
    static let title = "home"
    static let loading = "loading…"
    static let error = "couldn't load the home page — try refreshing"
}

enum HomeEditorCopy {
    static let edit = "edit"
    static let done = "done"
    static let placeholder = "home page content"
    static let saving = "saving…"
    static let saved = "saved ✓"
    static let saveError = "couldn't save"
}

enum HomeAutosaveStatus: Equatable {
    case idle, saving, saved, error
}

func showsHomeEdit(_ user: SessionUser?) -> Bool {
    guard let user else { return false }
    return user.isAdmin || user.permissions.contains("edit_homepage")
}

func homeAutosaveLabel(_ status: HomeAutosaveStatus) -> String? {
    switch status {
    case .idle: nil
    case .saving: HomeEditorCopy.saving
    case .saved: HomeEditorCopy.saved
    case .error: HomeEditorCopy.saveError
    }
}

@Observable
final class HomeEditorModel {
    var client: EventsClient
    var user: SessionUser?
    var page: HomePage?
    var editing = false
    var draft = ""
    var status: HomeAutosaveStatus = .idle
    var error: String?
    var autosaveDelay: Duration = .seconds(2)

    var canEdit: Bool { showsHomeEdit(user) }

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
            page = try await client.home()
        } catch {
            page = nil
            self.error = HomeCopy.error
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
                let page = try await self.client.updateHome(contentPm: value)
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

struct HomePage: Decodable, Equatable {
    var content: String
    var contentPm: String
    var contentHtml: String
    var updatedAt: String

    enum CodingKeys: String, CodingKey {
        case content
        case contentPm = "content_pm"
        case contentHtml = "content_html"
        case updatedAt = "updated_at"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        content = try c.decodeIfPresent(String.self, forKey: .content) ?? ""
        contentPm = try c.decodeIfPresent(String.self, forKey: .contentPm) ?? ""
        contentHtml = try c.decodeIfPresent(String.self, forKey: .contentHtml) ?? ""
        updatedAt = try c.decode(String.self, forKey: .updatedAt)
    }
}

func homeURL(base: URL) -> URL {
    URL(string: "/api/community/home/", relativeTo: base)!.absoluteURL
}

struct HomeView: View {
    var client = EventsClient()
    var user: SessionUser?
    @Environment(\.dismiss) private var dismiss
    @State private var model: HomeEditorModel?

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
                    ProgressView(HomeCopy.loading)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(PDAColor.background)
            .navigationTitle(HomeCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton("close", variant: .secondary) { dismiss() }
                }
            }
            .task {
                if model == nil { model = HomeEditorModel(client: client, user: user) }
                await model?.load()
            }
        }
    }

    @ViewBuilder
    private func editor(_ model: HomeEditorModel) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            if model.editing {
                HStack(spacing: 8) {
                    if let label = homeAutosaveLabel(model.status) {
                        Text(label)
                            .font(PDAType.control)
                            .foregroundStyle(autosaveColor(model.status))
                            .padding(.horizontal, 8)
                            .padding(.vertical, 2)
                            .background(autosaveFill(model.status), in: Capsule())
                    }
                    Spacer(minLength: 0)
                    PDAButton(HomeEditorCopy.done, variant: .ghost) {
                        Task { await model.done() }
                    }
                }
                .padding(.horizontal)
                PDATextField(
                    HomeEditorCopy.placeholder,
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
                        PDAButton(HomeEditorCopy.edit, variant: .ghost) { model.beginEdit() }
                    }
                    .padding(.horizontal)
                }
                if let html = model.page?.contentHtml {
                    ContentHTMLView(html: html, baseURL: client.baseURL)
                }
            }
        }
    }

    private func autosaveColor(_ status: HomeAutosaveStatus) -> Color {
        switch status {
        case .saved: PDAColor.success
        case .error: PDAColor.destructive
        case .saving, .idle: PDAColor.foregroundTertiary
        }
    }

    private func autosaveFill(_ status: HomeAutosaveStatus) -> Color {
        switch status {
        case .saved: PDAColor.successSubtle
        case .error: PDAColor.destructiveSubtle
        case .saving, .idle: PDAColor.surfaceDim
        }
    }
}

struct ContentHTMLView: UIViewRepresentable {
    let html: String
    let baseURL: URL

    func makeUIView(context: Context) -> WKWebView {
        let view = WKWebView(frame: .zero)
        view.isOpaque = false
        view.backgroundColor = .clear
        return view
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        webView.loadHTMLString(
            """
            <meta name="viewport" content="width=device-width, initial-scale=1">
            <style>body{font-family:-apple-system;margin:0;padding:16px;color:CanvasText;background:transparent}</style>
            \(html)
            """,
            baseURL: baseURL
        )
    }
}
