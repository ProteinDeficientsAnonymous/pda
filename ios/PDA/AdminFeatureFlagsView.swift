import SwiftUI

enum AdminFeatureFlagsCopy {
    static let title = "feature flags"
    static let loading = "loading…"
    static let error = "couldn't load feature flags — try refreshing"
    static let forbiddenTitle = "feature flags"
    static let forbiddenBody = "you need permission to manage feature flags to change a flag."
}

struct FeatureFlagChoice: Equatable {
    let key: String
    let label: String
}

let featureFlagChoices: [FeatureFlagChoice] = [
    FeatureFlagChoice(key: "host_attendance_report", label: "host attendance report"),
    FeatureFlagChoice(key: "admin_attendance_analytics", label: "admin attendance analytics"),
    FeatureFlagChoice(key: "event_payment_confirmation", label: "event payment confirmation"),
]

func featureFlagEnabled(_ flags: [String: Bool], _ key: String) -> Bool {
    flags[key] ?? false
}

func featureFlagEnvironmentLine(_ environment: String?) -> String {
    guard let environment else { return "loading environment…" }
    return "environment: \(environment.lowercased())"
}

@Observable
final class AdminFeatureFlagsModel {
    var client: EventsClient
    var flags: [String: Bool] = [:]
    var environment: String?
    var forbidden = false
    var error: String?
    var loaded = false
    var saving = false

    var explanationTitle: String { AdminFeatureFlagsCopy.forbiddenTitle }
    var explanationBody: String { AdminFeatureFlagsCopy.forbiddenBody }
    var environmentLine: String { featureFlagEnvironmentLine(environment) }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        async let flagsTask = client.featureFlags()
        async let versionTask = client.appVersion()
        do {
            flags = try await flagsTask
            loaded = true
        } catch {
            flags = [:]
            self.error = AdminFeatureFlagsCopy.error
            loaded = true
        }
        environment = try? await versionTask
    }

    func set(_ key: String, enabled: Bool) async {
        let previous = flags
        flags[key] = enabled
        saving = true
        defer { saving = false }
        do {
            flags = try await client.setFeatureFlag(key, enabled: enabled)
        } catch APIError.http(403) {
            flags = previous
            forbidden = true
        } catch {
            flags = previous
        }
    }
}

struct AdminFeatureFlagsView: View {
    var client: EventsClient
    @State private var model: AdminFeatureFlagsModel?

    var body: some View {
        Group {
            if let model, model.forbidden {
                VStack(alignment: .leading, spacing: 12) {
                    Text(model.explanationTitle).font(PDAType.field).fontWeight(.medium)
                    Text(model.explanationBody)
                        .font(PDAType.field)
                        .foregroundStyle(PDAColor.foregroundSecondary)
                    Spacer()
                }
                .padding()
                .frame(maxWidth: .infinity, alignment: .leading)
            } else if let model, let error = model.error {
                ContentUnavailableView {
                    Label(error, systemImage: "exclamationmark.triangle")
                } actions: {
                    PDAButton("try again") { Task { await model.load() } }
                }
            } else if let model, model.loaded {
                ScrollView {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(model.environmentLine)
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.muted)
                        VStack(spacing: 0) {
                            ForEach(featureFlagChoices, id: \.key) { choice in
                                Toggle(choice.label, isOn: binding(model, choice.key))
                                    .font(PDAType.control)
                                    .foregroundStyle(PDAColor.foreground)
                                    .tint(PDAColor.brand600)
                                    .disabled(model.saving)
                                    .padding(.vertical, 8)
                            }
                        }
                        .padding(.horizontal, 12)
                        .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.lg))
                        .overlay {
                            RoundedRectangle(cornerRadius: PDARadius.lg)
                                .strokeBorder(PDAColor.border, lineWidth: 1)
                        }
                    }
                    .padding()
                }
            } else {
                ProgressView(AdminFeatureFlagsCopy.loading)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        .background(PDAColor.background)
        .navigationTitle(AdminFeatureFlagsCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if model == nil { model = AdminFeatureFlagsModel(client: client) }
            await model?.load()
        }
    }

    private func binding(_ model: AdminFeatureFlagsModel, _ key: String) -> Binding<Bool> {
        Binding(
            get: { featureFlagEnabled(model.flags, key) },
            set: { enabled in Task { await model.set(key, enabled: enabled) } }
        )
    }
}
