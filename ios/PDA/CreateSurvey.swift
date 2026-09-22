import SwiftUI

enum CreateSurveyCopy {
    static let button = "new survey"
    static let title = "new survey"
    static let titleLabel = "title"
    static let slugLabel = "slug"
    static let slugHint = "short url segment — /surveys/:slug"
    static let descriptionLabel = "description (optional)"
    static let visibilityLabel = "visibility"
    static let membersOnly = "members only"
    static let publicVisibility = "public"
    static let linkedEvent = "linked event"
    static let none = "none"
    static let currentLinked = "current linked event"
    static let oneResponse = "one response per user"
    static let cancel = "cancel"
    static let create = "create"
    static let creating = "creating…"
    static let required = "title and slug are required"
    static let slugTaken = "a survey with that slug already exists"
    static let eventNotFound = "event not found"
    static let failure = "couldn't complete that action — try again"
    static let forbidden = "you don't have permission to do that"
}

enum CreateSurveyFieldError: Error, Equatable {
    case slug(String)
    case linkedEvent(String)
    case banner(String)
}

struct CreateSurveyInput: Equatable {
    var title = ""
    var description = ""
    var slug = ""
    var visibility = "members_only"
    var isActive = true
    var oneResponsePerUser = false
    var linkedEventId: String?

    static let empty = CreateSurveyInput()
}

struct CreatedSurvey: Decodable, Equatable {
    let id: String
}

struct SurveyEventOption: Equatable, Identifiable {
    let id: String
    let label: String
}

func clampedSurveyTitle(_ value: String) -> String { String(value.prefix(200)) }
func clampedSurveySlug(_ value: String) -> String { String(value.prefix(100)) }
func clampedSurveyDescription(_ value: String) -> String { String(value.prefix(2000)) }

func surveyLinkedEventLabel(title: String, start: Date?) -> String {
    let name = title.lowercased()
    guard let start else { return name }
    let formatter = DateFormatter()
    formatter.locale = Locale(identifier: "en_US_POSIX")
    formatter.timeZone = TimeZone(secondsFromGMT: 0)
    formatter.dateFormat = "MMM d, yyyy"
    return "\(name) · \(formatter.string(from: start).lowercased())"
}

func surveyEventOptions(events: [Event], selectedID: String?) -> [SurveyEventOption] {
    var options = events.map {
        SurveyEventOption(id: $0.id, label: surveyLinkedEventLabel(title: $0.title, start: $0.startDatetime))
    }
    if let selectedID, !selectedID.isEmpty, !options.contains(where: { $0.id == selectedID }) {
        options.insert(SurveyEventOption(id: selectedID, label: CreateSurveyCopy.currentLinked), at: 0)
    }
    return options
}

func createSurveyURL(base: URL) -> URL {
    URL(string: "/api/community/surveys/", relativeTo: base)!.absoluteURL
}

func createSurveyError(data: Data) -> CreateSurveyFieldError {
    let item = surveyAPIError(data)
    if item.field == "slug", item.code == "survey.slug_already_exists" {
        return .slug(CreateSurveyCopy.slugTaken)
    }
    if item.field == "linked_event_id", item.code == "event.not_found" {
        return .linkedEvent(CreateSurveyCopy.eventNotFound)
    }
    if item.code == "perm.denied" {
        return .banner(CreateSurveyCopy.forbidden)
    }
    return .banner(CreateSurveyCopy.failure)
}

private func surveyAPIError(_ data: Data) -> (code: String?, field: String?) {
    struct Envelope: Decodable {
        struct Item: Decodable {
            let code: String?
            let field: String?
        }
        let detail: [Item]?
    }
    let item = try? JSONDecoder().decode(Envelope.self, from: data).detail?.first
    return (item?.code, item?.field)
}

extension EventsClient {
    func createSurvey(_ input: CreateSurveyInput) async throws -> CreatedSurvey {
        var req = URLRequest(url: createSurveyURL(base: baseURL))
        req.httpMethod = "POST"
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        var body: [String: Any] = [
            "title": input.title,
            "description": input.description,
            "slug": input.slug,
            "visibility": input.visibility,
            "is_active": input.isActive,
            "one_response_per_user": input.oneResponsePerUser,
        ]
        body["linked_event_id"] = input.linkedEventId ?? NSNull()
        req.httpBody = try JSONSerialization.data(withJSONObject: body)
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw createSurveyError(data: data) }
        return try Event.decoder.decode(CreatedSurvey.self, from: data)
    }
}

@Observable
final class CreateSurveyModel {
    var client: EventsClient
    var input = CreateSurveyInput.empty
    var events: [Event] = []
    var slugError: String?
    var linkedEventError: String?
    var banner: String?
    var busy = false
    var createdID: String?

    init(client: EventsClient) {
        self.client = client
    }

    func loadEvents() async {
        events = (try? await client.events()) ?? []
    }

    func setSlug(_ value: String) {
        input.slug = clampedSurveySlug(value)
        slugError = nil
    }

    func setLinkedEvent(_ id: String?) {
        input.linkedEventId = id
        linkedEventError = nil
    }

    func submit() async {
        banner = nil
        slugError = nil
        linkedEventError = nil
        let title = input.title.trimmingCharacters(in: .whitespacesAndNewlines)
        let slug = input.slug.trimmingCharacters(in: .whitespacesAndNewlines)
        if title.isEmpty || slug.isEmpty {
            banner = CreateSurveyCopy.required
            return
        }
        busy = true
        defer { busy = false }
        do {
            createdID = try await client.createSurvey(input).id
        } catch let error as CreateSurveyFieldError {
            switch error {
            case let .slug(message):
                slugError = message
            case let .linkedEvent(message):
                linkedEventError = message
            case let .banner(message):
                banner = message
            }
        } catch {
            banner = CreateSurveyCopy.failure
        }
    }
}

struct CreateSurveySheet: View {
    var onCreated: () -> Void
    @Environment(\.dismiss) private var dismiss
    @State private var model: CreateSurveyModel

    init(client: EventsClient, onCreated: @escaping () -> Void) {
        self.onCreated = onCreated
        _model = State(initialValue: CreateSurveyModel(client: client))
    }

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    PDATextField(CreateSurveyCopy.titleLabel, text: titleText)
                    PDATextField(CreateSurveyCopy.slugLabel, text: slugText)
                    Text(CreateSurveyCopy.slugHint)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.foregroundSecondary)
                    if let slugError = model.slugError {
                        Text(slugError).font(PDAType.control).foregroundStyle(PDAColor.destructive)
                    }
                    PDATextField(CreateSurveyCopy.descriptionLabel, text: descriptionText, axis: .vertical)
                    labeledPicker(CreateSurveyCopy.visibilityLabel, selection: visibility) {
                        Text(CreateSurveyCopy.membersOnly).tag("members_only")
                        Text(CreateSurveyCopy.publicVisibility).tag("public")
                    }
                    labeledPicker(CreateSurveyCopy.linkedEvent, selection: linkedEvent) {
                        Text(CreateSurveyCopy.none).tag("")
                        ForEach(surveyEventOptions(events: model.events, selectedID: model.input.linkedEventId)) { option in
                            Text(option.label).tag(option.id)
                        }
                    }
                    if let linkedEventError = model.linkedEventError {
                        Text(linkedEventError).font(PDAType.control).foregroundStyle(PDAColor.destructive)
                    }
                    Toggle(CreateSurveyCopy.oneResponse, isOn: oneResponse)
                        .font(PDAType.field)
                        .foregroundStyle(PDAColor.foreground)
                    if let banner = model.banner {
                        Text(banner).font(PDAType.control).foregroundStyle(PDAColor.destructive)
                    }
                    HStack {
                        Spacer()
                        PDAButton(CreateSurveyCopy.cancel, variant: .ghost) { dismiss() }
                            .disabled(model.busy)
                        PDAButton(model.busy ? CreateSurveyCopy.creating : CreateSurveyCopy.create) {
                            Task { await model.submit() }
                        }
                        .disabled(model.busy)
                    }
                }
                .padding()
            }
            .background(PDAColor.background)
            .navigationTitle(CreateSurveyCopy.title)
            .navigationBarTitleDisplayMode(.inline)
        }
        .task { await model.loadEvents() }
        .onChange(of: model.createdID) { _, id in
            if id != nil { onCreated() }
        }
    }

    private var titleText: Binding<String> {
        Binding(
            get: { model.input.title },
            set: { model.input.title = clampedSurveyTitle($0) }
        )
    }

    private var slugText: Binding<String> {
        Binding(get: { model.input.slug }, set: { model.setSlug($0) })
    }

    private var descriptionText: Binding<String> {
        Binding(
            get: { model.input.description },
            set: { model.input.description = clampedSurveyDescription($0) }
        )
    }

    private var visibility: Binding<String> {
        Binding(get: { model.input.visibility }, set: { model.input.visibility = $0 })
    }

    private var linkedEvent: Binding<String> {
        Binding(
            get: { model.input.linkedEventId ?? "" },
            set: { model.setLinkedEvent($0.isEmpty ? nil : $0) }
        )
    }

    private var oneResponse: Binding<Bool> {
        Binding(
            get: { model.input.oneResponsePerUser },
            set: { model.input.oneResponsePerUser = $0 }
        )
    }

    private func labeledPicker<Content: View>(
        _ label: String,
        selection: Binding<String>,
        @ViewBuilder content: () -> Content
    ) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label).font(PDAType.control).foregroundStyle(PDAColor.foreground)
            Picker(label, selection: selection, content: content)
                .pickerStyle(.menu)
                .font(PDAType.field)
        }
    }
}
