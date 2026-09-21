import SwiftUI

struct EventListView: View {
    @State private var model = EventListModel()

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
            }
            .navigationDestination(for: Event.self) { event in
                EventDetailView(event: event)
            }
            .task { await model.load() }
        }
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
    let event: Event
    @State private var detail: Event
    @State private var loadError: String?

    init(event: Event) {
        self.event = event
        _detail = State(initialValue: event)
    }

    var body: some View {
        let copy = GuestEventCopy.make(detail)
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

                if !copy.description.isEmpty {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("about")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                        Text(copy.description.lowercased())
                    }
                }

                if let loadError {
                    Text(loadError)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

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
            detail = try await EventsClient().event(id: event.slug.isEmpty ? event.id : event.slug)
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
