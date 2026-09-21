import SwiftUI

struct EventListView: View {
    @Environment(AuthSession.self) private var session
    @State private var model = EventListModel()
    @State private var showLogin = false
    @State private var lockTitle = ""
    @State private var lockBody = ""
    @State private var showLock = false
    @State private var showMyRsvps = false

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
                    Button(PublicRsvpCopy.myRsvpsTitle) { showMyRsvps = true }
                    Spacer()
                    Button("directory") { open(directoryChrome(for: session.user)) }
                    Spacer()
                    Button("add event") { open(addEventChrome(for: session.user)) }
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

                if let myRsvp = copy.myRsvp {
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
            }
            .padding()
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .principal) {
                Text("event").font(.headline)
            }
        }
        .task { await refresh() }
    }

    private func refresh() async {
        do {
            detail = try await EventsClient(tokens: session.client.tokens)
                .event(id: event.slug.isEmpty ? event.id : event.slug)
            loadError = nil
        } catch APIError.http(404) {
            loadError = "this event isn't public or no longer exists"
        } catch APIError.http(403) {
            loadError = "you don't have permission to see this event"
        } catch {
            loadError = "couldn't load this event — try refreshing"
        }
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
