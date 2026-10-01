import SwiftUI

enum BottomNavCopy {
    static let items = ["calendar", "my rsvps", "add event", "members", "profile"]
}

enum BottomNavItem: Equatable {
    case calendar, myRsvps, addEvent, members, profile
}

enum BottomNavRoute: Equatable {
    case calendar
    case myEvents
    case guestRsvps
    case login
    case addEvent
    case members
    case profile
    case locked(title: String, body: String)
}

func bottomNavRoute(_ item: BottomNavItem, user: SessionUser?, hasGuestToken: Bool) -> BottomNavRoute {
    switch item {
    case .calendar:
        return .calendar
    case .myRsvps:
        switch myRsvpsDestination(user: user, hasGuestToken: hasGuestToken) {
        case .login: return .login
        case .guestRsvps: return .guestRsvps
        case .myEvents: return .myEvents
        }
    case .addEvent:
        switch addEventChrome(for: user) {
        case .login: return .login
        case .open: return .addEvent
        case let .locked(title, body): return .locked(title: title, body: body)
        }
    case .members:
        switch directoryChrome(for: user) {
        case .login: return .login
        case .open: return .members
        case let .locked(title, body): return .locked(title: title, body: body)
        }
    case .profile:
        return canShowProfile(user: user) ? .profile : .login
    }
}

struct BottomNavBar: View {
    static let height: CGFloat = 56

    var selected: BottomNavItem = .calendar
    var onSelect: (BottomNavItem) -> Void

    var body: some View {
        HStack(spacing: 0) {
            navLink(.calendar, BottomNavCopy.items[0])
            navLink(.myRsvps, BottomNavCopy.items[1])
            addEventLink
            navLink(.members, BottomNavCopy.items[3])
            navLink(.profile, BottomNavCopy.items[4])
        }
        .frame(maxWidth: .infinity)
        .frame(height: Self.height)
        .background(PDAColor.surface.ignoresSafeArea(edges: .bottom))
        .accessibilityElement(children: .contain)
        .accessibilityLabel("primary")
    }

    private func navLink(_ item: BottomNavItem, _ label: String) -> some View {
        let on = selected == item
        return Button {
            onSelect(item)
        } label: {
            VStack(spacing: 2) {
                Text(label)
                    .font(PDAType.control)
                    .foregroundStyle(on ? PDAColor.brand700 : PDAColor.muted)
                    .lineLimit(1)
                    .minimumScaleFactor(0.7)
                Circle()
                    .fill(PDAColor.brand700)
                    .frame(width: 4, height: 4)
                    .opacity(on ? 1 : 0)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }

    private var addEventLink: some View {
        let on = selected == .addEvent
        return Button {
            onSelect(.addEvent)
        } label: {
            Text("+")
                .font(PDAType.field)
                .foregroundStyle(PDAColor.brandOn)
                .frame(width: PDAMetrics.controlHeight, height: PDAMetrics.controlHeight)
                .background(
                    on ? PDAColor.brand700 : PDAColor.brand600,
                    in: RoundedRectangle(cornerRadius: PDARadius.lg)
                )
        }
        .buttonStyle(.plain)
        .frame(maxWidth: .infinity)
        .accessibilityLabel(BottomNavCopy.items[2])
    }
}
