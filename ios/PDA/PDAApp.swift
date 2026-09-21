import SwiftUI

@main
struct PDAApp: App {
    @State private var session = AuthSession()

    var body: some Scene {
        WindowGroup {
            EventListView()
                .environment(session)
                .task { await session.restore() }
        }
    }
}
