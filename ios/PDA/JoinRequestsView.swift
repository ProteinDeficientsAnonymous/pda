import SwiftUI

enum JoinRequestsCopy {
    static let title = "join requests"
    static let loading = "loading…"
    static let error = "couldn't load join requests — try refreshing"
    static let empty = "nothing here 🌿"
    static let noMatch = "nothing matches — try a different search"
    static let forbiddenTitle = "join requests"
    static let forbiddenBody = "you need permission to approve join requests to see this list."
    static let search = "name, phone, or email"
    static let filters = ["all", "pending", "tentative", "approved", "rejected"]
}

enum JoinRequestApproveCopy {
    static let button = "approve"
    static let title = "approve request"
    static let confirm = "approve"
    static let cancel = "cancel"
    static let error = "couldn't complete that action — try again"
}

enum JoinRequestRejectCopy {
    static let button = "reject"
    static let title = "reject request"
    static let confirm = "reject"
    static let cancel = "cancel"
    static let error = "couldn't complete that action — try again"
}

enum JoinRequestsError: Error, Equatable {
    case forbidden
}

struct JoinRequestRow: Decodable, Equatable, Identifiable {
    let id: String
    let fullName: String
    let phoneNumber: String
    let email: String
    let status: String
    let submittedAt: String
    let approvedAt: String?
    let rejectedAt: String?

    init(
        id: String,
        fullName: String,
        phoneNumber: String,
        email: String,
        status: String,
        submittedAt: String,
        approvedAt: String? = nil,
        rejectedAt: String? = nil
    ) {
        self.id = id
        self.fullName = fullName
        self.phoneNumber = phoneNumber
        self.email = email
        self.status = status
        self.submittedAt = submittedAt
        self.approvedAt = approvedAt
        self.rejectedAt = rejectedAt
    }

    enum CodingKeys: String, CodingKey {
        case id
        case fullName = "full_name"
        case phoneNumber = "phone_number"
        case email
        case status
        case submittedAt = "submitted_at"
        case approvedAt = "approved_at"
        case rejectedAt = "rejected_at"
    }

    init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: CodingKeys.self)
        id = try c.decode(String.self, forKey: .id)
        fullName = try c.decodeIfPresent(String.self, forKey: .fullName) ?? ""
        phoneNumber = try c.decodeIfPresent(String.self, forKey: .phoneNumber) ?? ""
        email = try c.decodeIfPresent(String.self, forKey: .email) ?? ""
        status = try c.decodeIfPresent(String.self, forKey: .status) ?? ""
        submittedAt = try c.decodeIfPresent(String.self, forKey: .submittedAt) ?? ""
        approvedAt = try c.decodeIfPresent(String.self, forKey: .approvedAt)
        rejectedAt = try c.decodeIfPresent(String.self, forKey: .rejectedAt)
    }
}

func joinRequestsURL(base: URL) -> URL {
    URL(string: "/api/community/join-requests/", relativeTo: base)!.absoluteURL
}

func joinRequestDecisionURL(base: URL, id: String) -> URL {
    URL(string: "/api/community/join-requests/\(id)/", relativeTo: base)!.absoluteURL
}

func joinRequestApproveName(_ row: JoinRequestRow) -> String {
    if !row.fullName.isEmpty { return row.fullName }
    return row.phoneNumber
}

func joinRequestApproveMessage(_ name: String) -> String {
    "approve \(name)? once you approve someone you can't un-approve them — are you sure?"
}

func joinRequestRejectMessage(_ name: String) -> String {
    "reject \(name)? once you reject someone you can't un-reject them — are you sure?"
}

struct JoinRequestDecision: Decodable, Equatable {
    let id: String
    let status: String
}

func visibleJoinRequests(_ rows: [JoinRequestRow], filter: String = "pending", query: String = "") -> [JoinRequestRow] {
    let q = query.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
    return rows
        .filter { row in
            (filter == "all" || row.status == filter) && joinRequestMatches(row, q)
        }
        .sorted { joinRequestSortKey($0) > joinRequestSortKey($1) }
}

func joinRequestsEmptyMessage(query: String) -> String {
    query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? JoinRequestsCopy.empty : JoinRequestsCopy.noMatch
}

private func joinRequestMatches(_ row: JoinRequestRow, _ query: String) -> Bool {
    if query.isEmpty { return true }
    return row.fullName.lowercased().contains(query)
        || row.phoneNumber.lowercased().contains(query)
        || row.email.lowercased().contains(query)
}

private func joinRequestSortKey(_ row: JoinRequestRow) -> String {
    row.approvedAt ?? row.rejectedAt ?? row.submittedAt
}

extension EventsClient {
    func joinRequests() async throws -> [JoinRequestRow] {
        var req = URLRequest(url: joinRequestsURL(base: baseURL))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        if status == 403 { throw JoinRequestsError.forbidden }
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode([JoinRequestRow].self, from: data)
    }

    func approveJoinRequest(id: String) async throws -> JoinRequestDecision {
        var req = URLRequest(url: joinRequestDecisionURL(base: baseURL, id: id))
        req.httpMethod = "PATCH"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: ["status": "approved"])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(JoinRequestDecision.self, from: data)
    }

    func rejectJoinRequest(id: String) async throws -> JoinRequestDecision {
        var req = URLRequest(url: joinRequestDecisionURL(base: baseURL, id: id))
        req.httpMethod = "PATCH"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        req.setValue("application/json", forHTTPHeaderField: "Content-Type")
        req.httpBody = try JSONSerialization.data(withJSONObject: ["status": "rejected"])
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        return try Event.decoder.decode(JoinRequestDecision.self, from: data)
    }
}

@Observable
final class JoinRequestsModel {
    var client: EventsClient
    var rows: [JoinRequestRow] = []
    var forbidden = false
    var error: String?
    var actionError: String?
    var pendingApprove: JoinRequestRow?
    var pendingReject: JoinRequestRow?
    var loaded = false

    var explanationTitle: String { JoinRequestsCopy.forbiddenTitle }
    var explanationBody: String { JoinRequestsCopy.forbiddenBody }

    init(client: EventsClient = EventsClient()) {
        self.client = client
    }

    func load() async {
        error = nil
        forbidden = false
        do {
            rows = try await client.joinRequests()
            loaded = true
        } catch JoinRequestsError.forbidden {
            rows = []
            forbidden = true
            loaded = true
        } catch {
            rows = []
            self.error = JoinRequestsCopy.error
            loaded = true
        }
    }

    func askApprove(_ row: JoinRequestRow) {
        guard row.status == "pending" else { return }
        pendingApprove = row
    }

    func cancelApprove() {
        pendingApprove = nil
    }

    func confirmApprove(_ row: JoinRequestRow) async {
        pendingApprove = nil
        actionError = nil
        do {
            let decision = try await client.approveJoinRequest(id: row.id)
            guard let index = rows.firstIndex(where: { $0.id == decision.id }) else { return }
            let current = rows[index]
            rows[index] = JoinRequestRow(
                id: current.id,
                fullName: current.fullName,
                phoneNumber: current.phoneNumber,
                email: current.email,
                status: decision.status,
                submittedAt: current.submittedAt,
                approvedAt: current.approvedAt,
                rejectedAt: current.rejectedAt
            )
        } catch {
            actionError = JoinRequestApproveCopy.error
        }
    }

    func askReject(_ row: JoinRequestRow) {
        guard row.status == "pending" else { return }
        pendingReject = row
    }

    func cancelReject() {
        pendingReject = nil
    }

    func confirmReject(_ row: JoinRequestRow) async {
        pendingReject = nil
        actionError = nil
        do {
            let decision = try await client.rejectJoinRequest(id: row.id)
            guard let index = rows.firstIndex(where: { $0.id == decision.id }) else { return }
            let current = rows[index]
            rows[index] = JoinRequestRow(
                id: current.id,
                fullName: current.fullName,
                phoneNumber: current.phoneNumber,
                email: current.email,
                status: decision.status,
                submittedAt: current.submittedAt,
                approvedAt: current.approvedAt,
                rejectedAt: current.rejectedAt
            )
        } catch {
            actionError = JoinRequestRejectCopy.error
        }
    }
}

struct JoinRequestsView: View {
    var client: EventsClient
    @State private var model: JoinRequestsModel?
    @State private var filter = "pending"
    @State private var query = ""
    @State private var editingWelcome = false
    @State private var editingTentative = false
    @State private var editingPromotion = false
    @State private var editingPromotionEmail = false
    @State private var editingWhatsApp = false
    @State private var welcomeNotice: String?
    @State private var tentativeNotice: String?
    @State private var promotionNotice: String?
    @State private var promotionEmailNotice: String?
    @State private var whatsAppNotice: String?

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
                    PDAButton("try again") { Task { await model.load() } }
                }
            } else if let model, model.loaded {
                let rows = visibleJoinRequests(model.rows, filter: filter, query: query)
                VStack(spacing: 8) {
                    ScrollView(.horizontal, showsIndicators: false) {
                        HStack {
                            PDAButton(WelcomeTemplateCopy.button, variant: .secondary) { editingWelcome = true }
                            PDAButton(TentativeApprovalCopy.button, variant: .secondary) { editingTentative = true }
                            PDAButton(MemberPromotionCopy.button, variant: .secondary) { editingPromotion = true }
                            PDAButton(MemberPromotionEmailCopy.button, variant: .secondary) { editingPromotionEmail = true }
                            PDAButton(WhatsAppLinkCopy.button, variant: .secondary) { editingWhatsApp = true }
                        }
                    }
                    .padding(.horizontal)
                    if let welcomeNotice {
                        Text(welcomeNotice)
                            .font(.footnote)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal)
                    }
                    if let tentativeNotice {
                        Text(tentativeNotice)
                            .font(.footnote)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal)
                    }
                    if let promotionNotice {
                        Text(promotionNotice)
                            .font(.footnote)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal)
                    }
                    if let promotionEmailNotice {
                        Text(promotionEmailNotice)
                            .font(.footnote)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal)
                    }
                    if let whatsAppNotice {
                        Text(whatsAppNotice)
                            .font(.footnote)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal)
                    }
                    Picker("filter", selection: $filter) {
                        ForEach(JoinRequestsCopy.filters, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .pickerStyle(.segmented)
                    .padding(.horizontal)
                    if rows.isEmpty {
                        ContentUnavailableView(joinRequestsEmptyMessage(query: query), systemImage: "tray")
                    } else {
                        List(rows) { row in
                            VStack(alignment: .leading, spacing: 2) {
                                Text(joinRequestTitle(row).lowercased())
                                if !row.phoneNumber.isEmpty {
                                    Text(row.phoneNumber.lowercased()).font(.footnote).foregroundStyle(.secondary)
                                }
                                if !row.email.isEmpty {
                                    Text(row.email.lowercased()).font(.footnote).foregroundStyle(.secondary)
                                }
                                Text(row.status.lowercased()).font(.footnote).foregroundStyle(.secondary)
                                if row.status == "pending" {
                                    PDAButton(JoinRequestApproveCopy.button) { model.askApprove(row) }
                                    PDAButton(JoinRequestRejectCopy.button, variant: .secondary) {
                                        model.askReject(row)
                                    }
                                }
                            }
                        }
                    }
                    if let actionError = model.actionError {
                        Text(actionError)
                            .font(PDAType.control)
                            .foregroundStyle(PDAColor.destructive)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .padding(.horizontal)
                    }
                }
            } else {
                ProgressView(JoinRequestsCopy.loading)
            }
        }
        .searchable(text: $query, prompt: JoinRequestsCopy.search)
        .navigationTitle(JoinRequestsCopy.title)
        .navigationBarTitleDisplayMode(.inline)
        .sheet(isPresented: $editingWelcome) {
            NavigationStack {
                WelcomeTemplateEditorView(client: client) {
                    welcomeNotice = WelcomeTemplateCopy.saved
                }
            }
        }
        .sheet(isPresented: $editingTentative) {
            NavigationStack {
                TentativeApprovalEditorView(client: client) {
                    tentativeNotice = TentativeApprovalCopy.saved
                }
            }
        }
        .sheet(isPresented: $editingPromotion) {
            NavigationStack {
                MemberPromotionEditorView(client: client) {
                    promotionNotice = MemberPromotionCopy.saved
                }
            }
        }
        .sheet(isPresented: $editingPromotionEmail) {
            NavigationStack {
                MemberPromotionEmailEditorView(client: client) {
                    promotionEmailNotice = MemberPromotionEmailCopy.saved
                }
            }
        }
        .sheet(isPresented: $editingWhatsApp) {
            NavigationStack {
                WhatsAppLinkEditorView(client: client) {
                    whatsAppNotice = WhatsAppLinkCopy.saved
                }
            }
        }
        .confirmationDialog(
            JoinRequestApproveCopy.title,
            isPresented: Binding(
                get: { model?.pendingApprove != nil },
                set: { if !$0 { model?.cancelApprove() } }
            ),
            titleVisibility: .visible
        ) {
            Button(JoinRequestApproveCopy.confirm) {
                guard let row = model?.pendingApprove else { return }
                Task { await model?.confirmApprove(row) }
            }
            Button(JoinRequestApproveCopy.cancel, role: .cancel) {
                model?.cancelApprove()
            }
        } message: {
            if let row = model?.pendingApprove {
                Text(joinRequestApproveMessage(joinRequestApproveName(row)))
            }
        }
        .confirmationDialog(
            JoinRequestRejectCopy.title,
            isPresented: Binding(
                get: { model?.pendingReject != nil },
                set: { if !$0 { model?.cancelReject() } }
            ),
            titleVisibility: .visible
        ) {
            Button(JoinRequestRejectCopy.confirm, role: .destructive) {
                guard let row = model?.pendingReject else { return }
                Task { await model?.confirmReject(row) }
            }
            Button(JoinRequestRejectCopy.cancel, role: .cancel) {
                model?.cancelReject()
            }
        } message: {
            if let row = model?.pendingReject {
                Text(joinRequestRejectMessage(joinRequestApproveName(row)))
            }
        }
        .task {
            if model == nil { model = JoinRequestsModel(client: client) }
            await model?.load()
        }
    }
}

private func joinRequestTitle(_ row: JoinRequestRow) -> String {
    if !row.fullName.isEmpty { return row.fullName }
    if !row.phoneNumber.isEmpty { return row.phoneNumber }
    return "join request"
}
