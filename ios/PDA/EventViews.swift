import SwiftUI

struct EventListView: View {
    @Environment(AuthSession.self) private var session
    @State private var model = EventListModel()
    @State private var showLogin = false
    @State private var lockTitle = ""
    @State private var lockBody = ""
    @State private var showLock = false
    @State private var showMyRsvps = false
    @State private var showMyEvents = false
    @State private var showAddEvent = false

    var body: some View {
        NavigationStack {
            Group {
                switch model.state {
                case .loading:
                    ProgressView("loading events")
                case let .failed(message):
                    ContentUnavailableView {
                        Label("couldn't load events", systemImage: "exclamationmark.triangle")
                    } description: {
                        Text(message)
                    } actions: {
                        Button("try again") { Task { await model.load() } }
                    }
                case let .loaded(events) where events.isEmpty:
                    ContentUnavailableView("nothing on the horizon — pop back later", systemImage: "leaf")
                case let .loaded(events):
                    List(events) { event in
                        NavigationLink(value: event) {
                            EventRow(event: event)
                        }
                    }
                    .listStyle(.plain)
                }
            }
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .principal) {
                    Text("calendar").font(.headline)
                }
                ToolbarItem(placement: .topBarTrailing) {
                    if session.user != nil {
                        Button("log out") { Task { await session.logout() } }
                    } else {
                        Button("sign in") { showLogin = true }
                    }
                }
                ToolbarItemGroup(placement: .bottomBar) {
                    Button(PublicRsvpCopy.myRsvpsTitle) { openMyRsvps() }
                    Spacer()
                    Button("directory") { open(directoryChrome(for: session.user)) }
                    Spacer()
                    Button("add event") { openAddEvent() }
                }
            }
            .sheet(isPresented: $showLogin) {
                LoginView(client: session.client)
                    .environment(session)
            }
            .sheet(isPresented: $showLock) {
                MemberLockSheet(title: lockTitle, message: lockBody)
            }
            .sheet(isPresented: $showMyRsvps) {
                MyRsvpsView()
            }
            .sheet(isPresented: $showMyEvents) {
                MyEventsView()
                    .environment(session)
            }
            .sheet(isPresented: $showAddEvent) {
                AddEventView {
                    Task { await model.load() }
                }
                .environment(session)
            }
            .fullScreenCover(isPresented: Binding(
                get: { authGate(for: session.user) != nil },
                set: { _ in }
            )) {
                GateView()
                    .environment(session)
                    .interactiveDismissDisabled()
            }
            .navigationDestination(for: Event.self) { event in
                EventDetailView(event: event)
            }
            .task {
                model.client.tokens = session.client.tokens
                await model.load()
            }
        }
    }

    private func open(_ chrome: MemberChrome) {
        switch chrome {
        case .login:
            showLogin = true
        case let .locked(title, body):
            lockTitle = title
            lockBody = body
            showLock = true
        case .open:
            break
        }
    }

    private func openAddEvent() {
        switch addEventChrome(for: session.user) {
        case .login:
            showLogin = true
        case let .locked(title, body):
            lockTitle = title
            lockBody = body
            showLock = true
        case .open:
            showAddEvent = true
        }
    }

    private func openMyRsvps() {
        switch myRsvpsDestination(user: session.user, hasGuestToken: RsvpTokenStore().load() != nil) {
        case .login:
            showLogin = true
        case .guestRsvps:
            showMyRsvps = true
        case .myEvents:
            showMyEvents = true
        }
    }
}

struct MemberLockSheet: View {
    @Environment(\.dismiss) private var dismiss
    let title: String
    let message: String

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 12) {
                Text(title).font(.title2)
                Text(message).font(.body).foregroundStyle(.secondary)
                Spacer()
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
        }
        .presentationDetents([.medium])
    }
}

struct EventRow: View {
    let event: Event

    var body: some View {
        let copy = GuestEventCopy.make(event)
        VStack(alignment: .leading, spacing: 4) {
            Text(copy.title.lowercased())
                .font(.headline)
            if let badge = copy.badge {
                Text(badge)
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            if !copy.when.isEmpty {
                Text(copy.when)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding(.vertical, 4)
    }
}

struct EventDetailView: View {
    @Environment(AuthSession.self) private var session
    let event: Event
    @State private var detail: Event
    @State private var loadError: String?
    @State private var showEdit = false
    @State private var showLogin = false
    @State private var showInvite = false
    @State private var showCheckIn = false
    @State private var showManageRsvps = false
    @State private var showCheckInReport = false
    @State private var hostAttendanceReport = false

    init(event: Event) {
        self.event = event
        _detail = State(initialValue: event)
    }

    var body: some View {
        let copy = GuestEventCopy.make(detail, user: session.user)
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let url = copy.photoURL {
                    AsyncImage(url: url) { image in
                        image.resizable().scaledToFit()
                    } placeholder: {
                        ProgressView()
                    }
                    .frame(maxHeight: 280)
                    .clipShape(RoundedRectangle(cornerRadius: 12))
                }

                HStack(alignment: .firstTextBaseline, spacing: 8) {
                    Text(copy.title.lowercased())
                        .font(.title2)
                        .fontWeight(.medium)
                    if let badge = copy.badge {
                        Text(badge)
                            .font(.caption)
                            .padding(.horizontal, 8)
                            .padding(.vertical, 3)
                            .background(.quaternary, in: Capsule())
                    }
                }

                Text(copy.when)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)

                if canShowCohostInvite(detail) {
                    CohostInviteBanner(
                        event: detail,
                        client: EventsClient(tokens: session.client.tokens)
                    ) { detail = $0 }
                }

                if canInviteGuests(detail, user: session.user) {
                    Button(InviteCopy.send) { showInvite = true }
                }

                if canShowCheckIn(detail, user: session.user) {
                    Button(CheckInCopy.title) { showCheckIn = true }
                }

                if canShowManageRsvps(detail, user: session.user) {
                    Button(ManageRsvpsCopy.title) { showManageRsvps = true }
                }

                if canShowCheckInReport(detail, user: session.user, flagOn: hostAttendanceReport) {
                    Button(CheckInReportCopy.title) { showCheckInReport = true }
                }

                if canShowEventPoll(detail, winningDatetime: nil) {
                    EventPollView(
                        eventId: detail.id,
                        signedIn: session.user != nil,
                        client: EventsClient(tokens: session.client.tokens),
                        onSignIn: { showLogin = true }
                    )
                }

                if let location = copy.location {
                    Text(location.lowercased())
                        .font(.subheadline)
                }

                if !copy.hosts.isEmpty {
                    Text("hosted by \(copy.hosts.joined(separator: ", ").lowercased())")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if let price = copy.price {
                    Text(price.lowercased())
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if !copy.tags.isEmpty {
                    HStack {
                        ForEach(copy.tags, id: \.self) { tag in
                            Text(tag.lowercased())
                                .font(.caption)
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(.quaternary, in: Capsule())
                        }
                    }
                }

                if let attending = copy.attending {
                    Text(attending)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if canShowMemberRsvp(detail, signedIn: session.user != nil) {
                    MemberRsvpView(
                        event: detail,
                        client: EventsClient(tokens: session.client.tokens)
                    ) { detail = $0 }
                } else if let myRsvp = copy.myRsvp {
                    Text("your rsvp: \(myRsvp.lowercased())")
                        .font(.subheadline)
                }

                if !copy.description.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("about")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text(copy.description.lowercased())
                    }
                }

                if !copy.links.isEmpty || copy.zelle != nil {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("links")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        ForEach(copy.links, id: \.url) { link in
                            Link(link.label, destination: link.url)
                        }
                        if let zelle = copy.zelle {
                            Text("zelle: \(zelle.lowercased())")
                                .font(.subheadline)
                        }
                    }
                }

                if !copy.rsvp.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("who's going")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        ForEach(Array(copy.rsvp.enumerated()), id: \.offset) { _, name in
                            Text(name.lowercased())
                        }
                    }
                }

                if let loadError {
                    Text(loadError)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                if !copy.moreHintTitle.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text(copy.moreHintTitle)
                            .font(.headline)
                        Text(copy.moreHintBody)
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    }
                    .padding()
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
                }

                if session.user == nil, canPublicRsvp(detail) {
                    PublicRsvpFormView(event: detail)
                }

                if canShowEventComments(
                    detail,
                    signedIn: session.user != nil,
                    hasGuestToken: RsvpTokenStore().load() != nil
                ) {
                    EventCommentsView(
                        eventId: detail.id,
                        guestToken: session.user == nil ? RsvpTokenStore().load() : nil,
                        client: EventsClient(tokens: session.client.tokens)
                    )
                }
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                Text("event").font(.headline)
            }
            if canEditEvent(detail, user: session.user) {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("edit") { showEdit = true }
                }
            }
        }
        .sheet(isPresented: $showEdit) {
            AddEventView(event: detail) {
                Task { await refresh() }
            }
            .environment(session)
        }
        .sheet(isPresented: $showLogin) {
            LoginView(client: session.client)
                .environment(session)
        }
        .sheet(isPresented: $showInvite) {
            InviteMembersView(
                event: detail,
                client: EventsClient(tokens: session.client.tokens)
            ) { detail = $0 }
            .environment(session)
        }
        .sheet(isPresented: $showCheckIn) {
            CheckInView(
                event: detail,
                client: EventsClient(tokens: session.client.tokens)
            ) { detail = $0 }
        }
        .sheet(isPresented: $showManageRsvps) {
            ManageRsvpsView(
                event: detail,
                client: EventsClient(tokens: session.client.tokens)
            ) { detail = $0 }
        }
        .sheet(isPresented: $showCheckInReport) {
            CheckInReportView(
                eventId: detail.id,
                client: EventsClient(tokens: session.client.tokens)
            )
        }
        .task { await refresh() }
    }

    private func refresh() async {
        let client = EventsClient(tokens: session.client.tokens)
        do {
            detail = try await client.event(id: event.slug.isEmpty ? event.id : event.slug)
            loadError = nil
        } catch APIError.http(404) {
            loadError = "this event isn't public or no longer exists"
        } catch APIError.http(403) {
            loadError = "you don't have permission to see this event"
        } catch {
            loadError = "couldn't load this event — try refreshing"
        }
        hostAttendanceReport = (try? await client.featureFlags())?["host_attendance_report"] ?? false
    }
}

@Observable
final class EventListModel {
    enum State {
        case loading
        case loaded([Event])
        case failed(String)
    }

    var state: State = .loading
    var client = EventsClient()

    func load() async {
        state = .loading
        do {
            let events = try await client.events()
                .filter(shouldShowOnCalendar)
                .sorted { ($0.startDatetime ?? .distantFuture) < ($1.startDatetime ?? .distantFuture) }
            state = .loaded(events)
        } catch {
            state = .failed("couldn't load events — try again")
        }
    }
}

@Observable
final class PublicRsvpModel {
    enum Step: Equatable { case phone, form, member, saved }

    var step: Step = .phone
    var phone = ""
    var firstName = ""
    var email = ""
    var status = "attending"
    var error: String?
    var busy = false
    let eventId: String
    var client: PublicRsvpClient

    init(eventId: String, client: PublicRsvpClient = PublicRsvpClient()) {
        self.eventId = eventId
        self.client = client
    }

    func submitPhone() async {
        error = nil
        busy = true
        defer { busy = false }
        do {
            switch try await client.checkPhone(eventId: eventId, phone: phone) {
            case .member: step = .member
            case .new, .nonMember: step = .form
            }
        } catch {
            self.error = "couldn't check your number — try again"
        }
    }

    func submitRsvp() async {
        error = nil
        busy = true
        defer { busy = false }
        do {
            _ = try await client.submit(
                eventId: eventId,
                phone: phone,
                firstName: firstName,
                email: email,
                status: status
            )
            step = .saved
        } catch {
            self.error = "couldn't save your rsvp — try again"
        }
    }
}

struct PublicRsvpFormView: View {
    @Environment(AuthSession.self) private var session
    @State private var model: PublicRsvpModel
    @State private var showLogin = false

    init(event: Event) {
        _model = State(initialValue: PublicRsvpModel(eventId: event.id))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(PublicRsvpCopy.title).font(.headline)
            if let error = model.error {
                Text(error).font(.subheadline).foregroundStyle(.secondary)
            }
            switch model.step {
            case .phone:
                TextField(PublicRsvpCopy.phoneLabel, text: $model.phone)
                    .textContentType(.telephoneNumber)
                    .keyboardType(.phonePad)
                Button(PublicRsvpCopy.continueButton) { Task { await model.submitPhone() } }
                    .disabled(model.busy || model.phone.isEmpty)
            case .form:
                TextField(PublicRsvpCopy.firstNameLabel, text: $model.firstName)
                    .textContentType(.givenName)
                TextField(PublicRsvpCopy.emailLabel, text: $model.email)
                    .textContentType(.emailAddress)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                Picker("status", selection: $model.status) {
                    Text(PublicRsvpCopy.going).tag("attending")
                    Text(PublicRsvpCopy.maybe).tag("maybe")
                }
                .pickerStyle(.segmented)
                Button(PublicRsvpCopy.submit) { Task { await model.submitRsvp() } }
                    .disabled(model.busy || model.firstName.isEmpty || model.email.isEmpty)
            case .member:
                Text(PublicRsvpCopy.memberBody)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                Button("sign in") { showLogin = true }
            case .saved:
                Text(PublicRsvpCopy.saved)
                    .font(.subheadline)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
        .sheet(isPresented: $showLogin) {
            LoginView(client: session.client)
                .environment(session)
        }
    }
}

struct MyRsvpsView: View {
    @Environment(\.dismiss) private var dismiss
    @State private var items: [PublicRsvpItem] = []
    @State private var message = PublicRsvpCopy.empty

    var body: some View {
        NavigationStack {
            Group {
                if items.isEmpty {
                    ContentUnavailableView(message, systemImage: "leaf")
                } else {
                    List(items, id: \.title) { item in
                        VStack(alignment: .leading) {
                            Text(item.title.lowercased())
                            Text(item.status.lowercased())
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }
            .navigationTitle(PublicRsvpCopy.myRsvpsTitle)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
            .task { await load() }
        }
    }

    private func load() async {
        guard let token = RsvpTokenStore().load() else {
            items = []
            message = PublicRsvpCopy.empty
            return
        }
        do {
            items = try await PublicRsvpClient().myRsvps(token: token)
            if items.isEmpty { message = PublicRsvpCopy.empty }
        } catch {
            items = []
            message = "couldn't load rsvps — try again"
        }
    }
}

struct MyEventsView: View {
    @Environment(AuthSession.self) private var session
    @Environment(\.dismiss) private var dismiss
    @State private var filter: MyEventsFilter = .upcoming
    @State private var active: [Event] = []
    @State private var drafts: [Event] = []
    @State private var cancelled: [Event] = []
    @State private var error: String?

    var body: some View {
        NavigationStack {
            Group {
                if let error {
                    ContentUnavailableView(error, systemImage: "exclamationmark.triangle")
                } else {
                    let userId = session.user?.id ?? ""
                    let pool = filter == .drafts ? drafts : filter == .cancelled ? cancelled : active
                    let items = myEvents(pool, userId: userId, filter: filter)
                    let filters = MyEventsFilter.allCases.filter {
                        !myEvents($0 == .drafts ? drafts : $0 == .cancelled ? cancelled : active, userId: userId, filter: $0).isEmpty
                    }
                    VStack {
                        if filters.count > 1 {
                            Picker("filter", selection: $filter) {
                                ForEach(filters, id: \.self) { item in
                                    Text(label(item)).tag(item)
                                }
                            }
                            .pickerStyle(.segmented)
                            .padding(.horizontal)
                        }
                        if items.isEmpty {
                            ContentUnavailableView(empty(filter), systemImage: "leaf")
                        } else {
                            List(items) { event in
                                NavigationLink(value: event) {
                                    EventRow(event: event)
                                }
                            }
                            .listStyle(.plain)
                        }
                    }
                    .navigationDestination(for: Event.self) { event in
                        EventDetailView(event: event)
                    }
                }
            }
            .navigationTitle(MyEventsCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
            .task { await load() }
        }
    }

    private func label(_ filter: MyEventsFilter) -> String {
        switch filter {
        case .upcoming: MyEventsCopy.upcoming
        case .hosting: MyEventsCopy.hosting
        case .past: MyEventsCopy.past
        case .drafts: MyEventsCopy.drafts
        case .cancelled: MyEventsCopy.cancelled
        }
    }

    private func empty(_ filter: MyEventsFilter) -> String {
        switch filter {
        case .upcoming: MyEventsCopy.emptyUpcoming
        case .hosting: MyEventsCopy.emptyHosting
        case .past: MyEventsCopy.emptyPast
        case .drafts: MyEventsCopy.emptyDrafts
        case .cancelled: MyEventsCopy.emptyCancelled
        }
    }

    private func load() async {
        var client = EventsClient()
        client.tokens = session.client.tokens
        do {
            async let a = client.events()
            async let d = client.events(status: "draft")
            async let c = client.events(status: "cancelled")
            active = try await a
            drafts = try await d
            cancelled = try await c
            error = nil
        } catch {
            self.error = "couldn't load events — try refreshing"
        }
    }
}

struct AddEventView: View {
    @Environment(AuthSession.self) private var session
    @Environment(\.dismiss) private var dismiss
    var event: Event?
    var onCreated: () -> Void

    @State private var title: String
    @State private var start: Date
    @State private var description: String
    @State private var eventType = "community"
    @State private var error: String?
    @State private var busy = false

    init(event: Event? = nil, onCreated: @escaping () -> Void) {
        self.event = event
        self.onCreated = onCreated
        _title = State(initialValue: event?.title ?? "")
        _start = State(initialValue: event?.startDatetime ?? Date())
        _description = State(initialValue: event?.description ?? "")
    }

    var body: some View {
        NavigationStack {
            Form {
                TextField(AddEventCopy.titleLabel, text: $title)
                DatePicker(AddEventCopy.whenLabel, selection: $start)
                    .datePickerStyle(.compact)
                TextField(AddEventCopy.descriptionLabel, text: $description, axis: .vertical)
                    .lineLimit(3 ... 8)
                let types = session.user.map(allowedEventTypes) ?? ["community"]
                if event == nil, types.count > 1 {
                    Picker("type", selection: $eventType) {
                        ForEach(types, id: \.self) { type in
                            Text(typeLabel(type)).tag(type)
                        }
                    }
                }
                if let error {
                    Text(error).foregroundStyle(.secondary)
                }
            }
            .navigationTitle(event == nil ? AddEventCopy.title : EditEventCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(event == nil ? AddEventCopy.save : EditEventCopy.save) { Task { await save() } }
                        .disabled(busy || title.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
    }

    private func typeLabel(_ type: String) -> String {
        switch type {
        case "official": AddEventCopy.typeOfficial
        case "club": AddEventCopy.typeClub
        default: AddEventCopy.typeCommunity
        }
    }

    private func save() async {
        error = nil
        busy = true
        defer { busy = false }
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime]
        var client = EventsClient()
        client.tokens = session.client.tokens
        do {
            if let event {
                _ = try await client.update(
                    id: event.id,
                    title: title,
                    start: formatter.string(from: start),
                    description: description
                )
            } else {
                _ = try await client.create(
                    title: title,
                    start: formatter.string(from: start),
                    description: description,
                    eventType: eventType
                )
            }
            onCreated()
            dismiss()
        } catch {
            self.error = "couldn't save this event — try again"
        }
    }
}

struct EventCommentsView: View {
    let eventId: String
    var guestToken: String?
    var client: EventsClient

    @State private var list: EventCommentList?
    @State private var error: String?
    @State private var draft = ""
    @State private var busy = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(EventCommentCopy.title)
                .font(.headline)
            if let list {
                if let prompt = commentComposerPrompt(canPost: list.canPost, reason: list.cannotPostReason) {
                    Text(prompt)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                } else {
                    TextField(EventCommentCopy.placeholder, text: $draft, axis: .vertical)
                        .lineLimit(2 ... 5)
                    Button(EventCommentCopy.post) { Task { await post() } }
                        .disabled(busy || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                ForEach(visibleComments(list)) { comment in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(comment.authorDisplayName.lowercased())
                            .font(.subheadline)
                        Text(comment.isDeleted ? "[deleted]" : comment.body)
                        HStack {
                            ForEach(comment.reactions, id: \.emoji) { reaction in
                                Button("\(reaction.emoji) \(reaction.count)") {
                                    Task { await react(comment.id, reaction.emoji) }
                                }
                            }
                            Menu {
                                ForEach(reactionEmojis, id: \.self) { emoji in
                                    Button(emoji) { Task { await react(comment.id, emoji) } }
                                }
                            } label: {
                                Text("＋")
                            }
                            .accessibilityLabel("add reaction")
                        }
                    }
                }
            } else if let error {
                Text(error)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ProgressView("loading…")
            }
        }
        .task { await load() }
    }

    private func load() async {
        do {
            list = try await client.comments(eventId: eventId, guestToken: guestToken)
            error = nil
        } catch {
            self.error = EventCommentCopy.loadError
        }
    }

    private func post() async {
        let body = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !body.isEmpty else { return }
        busy = true
        defer { busy = false }
        do {
            _ = try await client.postComment(eventId: eventId, body: body, guestToken: guestToken)
            draft = ""
            await load()
        } catch {
            self.error = "couldn't post your comment"
        }
    }

    private func react(_ commentId: String, _ emoji: String) async {
        do {
            _ = try await client.toggleReaction(
                eventId: eventId,
                commentId: commentId,
                emoji: emoji,
                guestToken: guestToken
            )
            await load()
        } catch {
            self.error = "couldn't save that reaction"
        }
    }
}

struct EventPollView: View {
    let eventId: String
    let signedIn: Bool
    var client: EventsClient
    var onSignIn: () -> Void

    @State private var poll: EventPoll?
    @State private var error: String?
    @State private var busy = false

    var body: some View {
        if poll?.winningDatetime != nil {
            EmptyView()
        } else {
            content
        }
    }

    private var content: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(EventPollCopy.title)
                .font(.headline)
            if let poll {
                ForEach(sortPollOptionsByVotes(poll.options)) { option in
                    VStack(alignment: .leading, spacing: 6) {
                        Text(
                            formatEventDateTime(
                                start: option.datetime,
                                end: nil,
                                datetimeTbd: option.datetime == nil
                            )
                        )
                        .font(.subheadline)
                        Text("\(EventPollCopy.yes) \(option.yesCount) · \(EventPollCopy.maybe) \(option.maybeCount) · \(EventPollCopy.no) \(option.noCount)")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        if pollVoteChrome(signedIn: signedIn) == .vote {
                            HStack {
                                ForEach([EventPollCopy.yes, EventPollCopy.maybe, EventPollCopy.no], id: \.self) { choice in
                                    Button(choice) { Task { await vote(option.id, choice) } }
                                        .disabled(busy)
                                        .fontWeight(poll.myVotes[option.id] == choice ? .bold : .regular)
                                }
                            }
                        }
                    }
                }
                if pollVoteChrome(signedIn: signedIn) == .login {
                    Button(EventPollCopy.signIn, action: onSignIn)
                }
            } else if let error {
                Text(error)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            } else {
                ProgressView("loading poll…")
            }
        }
        .task { await load() }
    }

    private func load() async {
        do {
            poll = try await client.poll(eventId: eventId)
            error = nil
        } catch {
            self.error = EventPollCopy.loadError
        }
    }

    private func vote(_ optionId: String, _ choice: String) async {
        guard let poll else { return }
        busy = true
        defer { busy = false }
        do {
            self.poll = try await client.votePoll(
                eventId: eventId,
                votes: mergedPollVotes(current: poll.myVotes, optionId: optionId, choice: choice)
            )
        } catch {
            self.error = "couldn't update the poll — try again"
        }
    }
}

struct CohostInviteBanner: View {
    let event: Event
    var client: EventsClient
    var onUpdated: (Event) -> Void

    @State private var busy = false
    @State private var error: String?

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(cohostInviteMessage(createdByName: event.createdByName))
            HStack {
                Button(CohostInviteCopy.accept) { Task { await respond(accept: true) } }
                    .disabled(busy)
                Button(CohostInviteCopy.decline) { Task { await respond(accept: false) } }
                    .disabled(busy)
            }
            if let error {
                Text(error)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
        }
        .padding()
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(.thinMaterial, in: RoundedRectangle(cornerRadius: 12))
    }

    private func respond(accept: Bool) async {
        guard let inviteId = event.myPendingCohostInviteId else { return }
        busy = true
        defer { busy = false }
        do {
            let updated = if accept {
                try await client.acceptCohostInvite(eventId: event.id, inviteId: inviteId)
            } else {
                try await client.declineCohostInvite(eventId: event.id, inviteId: inviteId)
            }
            onUpdated(updated)
        } catch {
            self.error = "couldn't update that invite — try again"
        }
    }
}

struct MemberRsvpView: View {
    let event: Event
    var client: EventsClient
    var onUpdated: (Event) -> Void

    @State private var status: String
    @State private var answers: [String: String]
    @State private var error: String?
    @State private var busy = false

    init(event: Event, client: EventsClient, onUpdated: @escaping (Event) -> Void) {
        self.event = event
        self.client = client
        self.onUpdated = onUpdated
        _status = State(initialValue: event.myRsvp.isEmpty ? "attending" : event.myRsvp)
        _answers = State(initialValue: Dictionary(uniqueKeysWithValues: event.rsvpQuestions.map { ($0.id, "") }))
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text(PublicRsvpCopy.title).font(.headline)
            HStack {
                statusButton(MemberRsvpCopy.going, "attending")
                statusButton(MemberRsvpCopy.maybe, "maybe")
                statusButton(MemberRsvpCopy.cantGo, "cant_go")
            }
            if rsvpQuestionsApplyToStatus(status), !event.rsvpQuestions.isEmpty {
                Text(RsvpQuestionCopy.title)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
                ForEach(event.rsvpQuestions) { question in
                    questionField(question)
                }
            }
            if let error {
                Text(error)
                    .font(.subheadline)
                    .foregroundStyle(.secondary)
            }
            Button(MemberRsvpCopy.save) { Task { await save() } }
                .disabled(busy)
        }
    }

    private func statusButton(_ label: String, _ value: String) -> some View {
        Button(label) { status = value }
            .fontWeight(status == value ? .bold : .regular)
    }

    @ViewBuilder
    private func questionField(_ question: EventRsvpQuestion) -> some View {
        let label = question.label.lowercased()
        switch question.fieldType {
        case "select":
            Picker(label, selection: answerBinding(question.id)) {
                Text("").tag("")
                ForEach(question.options, id: \.self) { option in
                    Text(option.lowercased()).tag(option)
                }
            }
        case "checkbox":
            Toggle(label, isOn: Binding(
                get: { !(answers[question.id] ?? "").isEmpty },
                set: { answers[question.id] = $0 ? "yes" : "" }
            ))
        default:
            TextField(label, text: answerBinding(question.id), axis: .vertical)
                .textInputAutocapitalization(.never)
        }
    }

    private func answerBinding(_ id: String) -> Binding<String> {
        Binding(get: { answers[id] ?? "" }, set: { answers[id] = $0 })
    }

    private func save() async {
        let payload: [String: String]
        if rsvpQuestionsApplyToStatus(status) {
            let missing = missingRequiredQuestionIds(event.rsvpQuestions, answers: answers)
            if !missing.isEmpty {
                error = MemberRsvpCopy.required
                return
            }
            payload = answers.filter { !$0.value.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty }
        } else {
            payload = [:]
        }
        busy = true
        defer { busy = false }
        do {
            let updated = try await client.setRsvp(eventId: event.id, status: status, answers: payload)
            error = nil
            onUpdated(updated)
        } catch {
            self.error = "couldn't save your rsvp — try again"
        }
    }
}

struct CheckInView: View {
    let event: Event
    var client: EventsClient
    var onUpdated: (Event) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var current: Event
    @State private var error: String?
    @State private var busy = false

    init(event: Event, client: EventsClient, onUpdated: @escaping (Event) -> Void) {
        self.event = event
        self.client = client
        self.onUpdated = onUpdated
        _current = State(initialValue: event)
    }

    var body: some View {
        NavigationStack {
            List {
                if !isCheckInOpen(current) {
                    Text(CheckInCopy.opensLater)
                } else if current.guests.isEmpty {
                    Text(CheckInCopy.empty)
                } else {
                    ForEach(current.guests, id: \.userId) { guest in
                        HStack {
                            Text(guest.name.lowercased())
                            Spacer()
                            Button(CheckInCopy.attended) { Task { await mark(guest.userId, "attended") } }
                                .fontWeight(guest.attendance == "attended" ? .bold : .regular)
                                .disabled(busy)
                            Button(CheckInCopy.didntAttend) { Task { await mark(guest.userId, "didnt_go") } }
                                .fontWeight(guest.attendance == "didnt_go" ? .bold : .regular)
                                .disabled(busy)
                        }
                    }
                }
                if let error {
                    Text(error).foregroundStyle(.secondary)
                }
            }
            .navigationTitle(CheckInCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
        }
    }

    private func mark(_ userId: String, _ attendance: String) async {
        busy = true
        defer { busy = false }
        do {
            let updated = try await client.setAttendance(
                eventId: current.id,
                userId: userId,
                attendance: attendance
            )
            current = updated
            error = nil
            onUpdated(updated)
        } catch {
            self.error = "couldn't save check-in — try again"
        }
    }
}

struct CheckInReportView: View {
    let eventId: String
    var client: EventsClient

    @Environment(\.dismiss) private var dismiss
    @State private var report: CheckInReport?
    @State private var error: String?

    var body: some View {
        NavigationStack {
            List {
                if let report {
                    section(CheckInReportCopy.attended, report.attended)
                    section(CheckInReportCopy.noShows, report.noShows)
                    section(CheckInReportCopy.didntGo, report.didntGo)
                    section(CheckInReportCopy.canceled, report.canceled)
                    section(CheckInReportCopy.unmarked, report.unmarked)
                } else if let error {
                    Text(error).foregroundStyle(.secondary)
                } else {
                    ProgressView()
                }
            }
            .navigationTitle(CheckInReportCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
            .task { await load() }
        }
    }

    @ViewBuilder
    private func section(_ title: String, _ people: [CheckInReportPerson]) -> some View {
        if !people.isEmpty {
            Section(title) {
                ForEach(people, id: \.name) { person in
                    Text(person.name.lowercased())
                }
            }
        }
    }

    private func load() async {
        do {
            report = try await client.checkInReport(eventId: eventId)
            error = nil
        } catch {
            self.error = "couldn't load the check-in report — try refreshing"
        }
    }
}

struct ManageRsvpsView: View {
    let event: Event
    var client: EventsClient
    var onUpdated: (Event) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var current: Event
    @State private var error: String?
    @State private var busy = false

    init(event: Event, client: EventsClient, onUpdated: @escaping (Event) -> Void) {
        self.event = event
        self.client = client
        self.onUpdated = onUpdated
        _current = State(initialValue: event)
    }

    var body: some View {
        NavigationStack {
            List {
                if current.guests.isEmpty {
                    Text(ManageRsvpsCopy.empty)
                } else {
                    ForEach(current.guests, id: \.userId) { guest in
                        VStack(alignment: .leading, spacing: 8) {
                            Text(guest.name.lowercased())
                            HStack {
                                statusButton(guest, ManageRsvpsCopy.going, "attending")
                                statusButton(guest, ManageRsvpsCopy.maybe, "maybe")
                                statusButton(guest, ManageRsvpsCopy.cantGo, "cant_go")
                            }
                        }
                    }
                }
                if let error {
                    Text(error).foregroundStyle(.secondary)
                }
            }
            .navigationTitle(ManageRsvpsCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("close") { dismiss() }
                }
            }
        }
    }

    private func statusButton(_ guest: EventGuest, _ label: String, _ status: String) -> some View {
        Button(label) { Task { await setStatus(guest.userId, status) } }
            .fontWeight(guest.status == status ? .bold : .regular)
            .disabled(busy)
    }

    private func setStatus(_ userId: String, _ status: String) async {
        busy = true
        defer { busy = false }
        do {
            let updated = try await client.setGuestRsvp(
                eventId: current.id,
                userId: userId,
                status: status
            )
            current = updated
            error = nil
            onUpdated(updated)
        } catch {
            self.error = "couldn't save that rsvp — try again"
        }
    }
}

struct InviteMembersView: View {
    let event: Event
    var client: EventsClient
    var onUpdated: (Event) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var query = ""
    @State private var hits: [MemberHit] = []
    @State private var selected: [MemberHit] = []
    @State private var error: String?
    @State private var busy = false

    var body: some View {
        NavigationStack {
            List {
                Section {
                    TextField(InviteCopy.search, text: $query)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .onChange(of: query) { _, value in
                            Task { await search(value) }
                        }
                }
                Section {
                    ForEach(hits.filter { hit in
                        !event.invitedUserIds.contains(hit.id)
                            && !event.coHostIds.contains(hit.id)
                            && !selected.contains(where: { $0.id == hit.id })
                    }) { hit in
                        Button(hit.name.lowercased()) { selected.append(hit) }
                    }
                }
                if !selected.isEmpty {
                    Section {
                        ForEach(selected) { hit in
                            Text(hit.name.lowercased())
                        }
                    }
                }
                if let error {
                    Text(error).foregroundStyle(.secondary)
                }
            }
            .navigationTitle(InviteCopy.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(InviteCopy.cancel) { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("\(InviteCopy.send) \(selected.count)") { Task { await send() } }
                        .disabled(busy || selected.isEmpty)
                }
            }
        }
    }

    private func search(_ value: String) async {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard trimmed.count >= 2 else {
            hits = []
            return
        }
        do {
            hits = try await client.searchMembers(query: trimmed)
            error = nil
        } catch {
            self.error = "couldn't search members — try again"
        }
    }

    private func send() async {
        busy = true
        defer { busy = false }
        do {
            let updated = try await client.inviteGuests(eventId: event.id, userIds: selected.map(\.id))
            onUpdated(updated)
            dismiss()
        } catch {
            self.error = "couldn't send invites — try again"
        }
    }
}
