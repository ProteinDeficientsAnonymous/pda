import SwiftUI

@main
struct PDAApp: App {
    @State private var session = AuthSession()
    @State private var a11y = AccessibilityStore()

    var body: some Scene {
        WindowGroup {
            EventListView()
                .environment(session)
                .environment(a11y)
                .preferredColorScheme(a11y.colorScheme)
                .dynamicTypeSize(a11y.typeSize)
                .font(a11y.dyslexiaFont ? Font.custom("OpenDyslexic", size: 17, relativeTo: .body) : nil)
                .task { await session.restore() }
        }
    }
}

extension AccessibilityStore {
    var colorScheme: ColorScheme? {
        switch themeMode {
        case .system: nil
        case .light: .light
        case .dark: .dark
        }
    }

    var typeSize: DynamicTypeSize {
        switch textScale {
        case .normal: .large
        case .medium: .xLarge
        case .large: .xxLarge
        }
    }
}
