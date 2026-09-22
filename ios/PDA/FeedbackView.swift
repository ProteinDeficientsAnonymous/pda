import SwiftUI
import UIKit

struct FeedbackResult: Decodable {
    let htmlURL: String

    enum CodingKeys: String, CodingKey {
        case htmlURL = "html_url"
    }
}

enum FeedbackCopy {
    static let button = "send feedback"
    static let mark = "?"
    static let title = "title"
    static let description = "description"
    static let bug = "bug"
    static let feature = "feature request"
    static let improvement = "improvement"
    static let cancel = "cancel"
    static let submit = "submit"
    static let sending = "sending..."
    static let required = "required"
    static let saved = "feedback submitted — thanks! 🌱"
    static let viewIssue = "view your issue"
    static let failed = "couldn't submit feedback — try again"
    static let titleMax = 150
    static let descriptionMax = 2000
}

func showsFeedbackControl(for user: SessionUser?) -> Bool {
    user != nil
}

@Observable
final class FeedbackModel {
    var open = false
    var title = ""
    var description = ""
    var bug = false
    var feature = false
    var improvement = false
    var titleError: String?
    var descriptionError: String?
    var sending = false
    var toast: String?
    var issueURL: URL?
    let route: String
    let userAgent: String
    let client: EventsClient

    var submitLabel: String { sending ? FeedbackCopy.sending : FeedbackCopy.submit }
    var issueLabel: String? { issueURL == nil ? nil : FeedbackCopy.viewIssue }

    init(client: EventsClient, route: String, userAgent: String) {
        self.client = client
        self.route = route
        self.userAgent = userAgent
    }

    func setTitle(_ value: String) {
        title = String(value.prefix(FeedbackCopy.titleMax))
    }

    func setDescription(_ value: String) {
        description = String(value.prefix(FeedbackCopy.descriptionMax))
    }

    func cancel() {
        open = false
        title = ""
        description = ""
        bug = false
        feature = false
        improvement = false
        titleError = nil
        descriptionError = nil
    }

    func submit() async {
        let trimmedTitle = title.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedDescription = description.trimmingCharacters(in: .whitespacesAndNewlines)
        titleError = trimmedTitle.isEmpty ? FeedbackCopy.required : nil
        descriptionError = trimmedDescription.isEmpty ? FeedbackCopy.required : nil
        if titleError != nil || descriptionError != nil { return }
        sending = true
        defer { sending = false }
        var types: [String] = []
        if bug { types.append(FeedbackCopy.bug) }
        if feature { types.append(FeedbackCopy.feature) }
        if improvement { types.append(FeedbackCopy.improvement) }
        do {
            let result = try await client.submitFeedback(
                title: trimmedTitle,
                description: trimmedDescription,
                types: types,
                route: route,
                userAgent: userAgent
            )
            toast = FeedbackCopy.saved
            issueURL = result.htmlURL.isEmpty ? nil : URL(string: result.htmlURL)
            cancel()
        } catch {
            toast = FeedbackCopy.failed
            issueURL = nil
        }
    }
}

struct FeedbackButton: View {
    @State private var model: FeedbackModel

    init(client: EventsClient, route: String = "/calendar", userAgent: String? = nil) {
        _model = State(initialValue: FeedbackModel(
            client: client,
            route: route,
            userAgent: userAgent ?? Self.deviceUserAgent()
        ))
    }

    var body: some View {
        VStack(alignment: .trailing, spacing: 8) {
            if !model.open, model.toast == FeedbackCopy.saved {
                Text(FeedbackCopy.saved)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foreground)
                if let url = model.issueURL {
                    Link(FeedbackCopy.viewIssue, destination: url)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.brand600)
                }
            }
            Button {
                model.open = true
            } label: {
                Text(FeedbackCopy.mark)
                    .font(PDAType.field)
                    .fontWeight(.semibold)
                    .foregroundStyle(PDAColor.brandOn)
                    .frame(width: 48, height: 48)
                    .background(PDAColor.brand600, in: Circle())
            }
            .accessibilityLabel(FeedbackCopy.button)
        }
        .sheet(isPresented: Binding(
            get: { model.open },
            set: { if !$0 { model.cancel() } }
        )) {
            form
        }
    }

    private var form: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text(FeedbackCopy.button)
                .font(PDAType.field)
                .fontWeight(.medium)
                .foregroundStyle(PDAColor.foreground)
            PDATextField(FeedbackCopy.title, text: titleBinding)
            if let titleError = model.titleError {
                Text(titleError)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.destructive)
            }
            PDATextField(
                FeedbackCopy.description,
                text: descriptionBinding,
                axis: .vertical,
                lineLimit: 5,
                reserveLineSpace: true
            )
            if let descriptionError = model.descriptionError {
                Text(descriptionError)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.destructive)
            }
            Toggle(FeedbackCopy.bug, isOn: Bindable(model).bug)
                .font(PDAType.control)
                .tint(PDAColor.brand600)
            Toggle(FeedbackCopy.feature, isOn: Bindable(model).feature)
                .font(PDAType.control)
                .tint(PDAColor.brand600)
            Toggle(FeedbackCopy.improvement, isOn: Bindable(model).improvement)
                .font(PDAType.control)
                .tint(PDAColor.brand600)
            if model.toast == FeedbackCopy.failed {
                Text(FeedbackCopy.failed)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.destructive)
            }
            HStack {
                Spacer()
                PDAButton(FeedbackCopy.cancel, variant: .secondary) { model.cancel() }
                    .disabled(model.sending)
                PDAButton(model.submitLabel) { Task { await model.submit() } }
                    .disabled(model.sending)
            }
        }
        .padding(16)
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(PDAColor.surface)
    }

    private var titleBinding: Binding<String> {
        Binding(get: { model.title }, set: { model.setTitle($0) })
    }

    private var descriptionBinding: Binding<String> {
        Binding(get: { model.description }, set: { model.setDescription($0) })
    }

    private static func deviceUserAgent() -> String {
        "\(UIDevice.current.systemName) \(UIDevice.current.systemVersion)"
    }
}
