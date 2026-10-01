import SwiftUI

enum MenuSheetCopy {
    static let open = "open menu"
    static let menu = "menu"
    static let close = "close menu"
    static let guidelines = "guidelines"
    static let logOut = "log out"
}

enum MenuSheetRoute: Equatable {
    case home, faq, donate, guidelines, volunteer, settings, logOut
}

struct MenuSheetEntry: Equatable {
    var label: String
    var route: MenuSheetRoute
}

func menuSheetItems(user: SessionUser?) -> [MenuSheetEntry] {
    var items = [
        MenuSheetEntry(label: HomeCopy.title, route: .home),
        MenuSheetEntry(label: FaqCopy.title, route: .faq),
        MenuSheetEntry(label: DonateCopy.title, route: .donate),
    ]
    if user != nil {
        items += [
            MenuSheetEntry(label: MenuSheetCopy.guidelines, route: .guidelines),
            MenuSheetEntry(label: VolunteerCopy.title, route: .volunteer),
            MenuSheetEntry(label: SettingsCopy.title, route: .settings),
            MenuSheetEntry(label: MenuSheetCopy.logOut, route: .logOut),
        ]
    }
    return items
}

struct MenuSheet: View {
    let user: SessionUser?
    var onSelect: (MenuSheetRoute) -> Void
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        let items = menuSheetItems(user: user)
        let pages = items.filter { $0.route != .logOut }
        let account = items.filter { $0.route == .logOut }
        NavigationStack {
            List {
                Section {
                    ForEach(pages, id: \.label) { row($0) }
                }
                if !account.isEmpty {
                    Section {
                        ForEach(account, id: \.label) { row($0) }
                    }
                }
            }
            .listStyle(.plain)
            .scrollContentBackground(.hidden)
            .background(PDAColor.surface)
            .navigationTitle(MenuSheetCopy.menu)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    PDAButton(MenuSheetCopy.close, variant: .ghost) { dismiss() }
                }
            }
        }
        .presentationDetents([.medium])
        .presentationDragIndicator(.visible)
        .presentationCornerRadius(PDARadius.md)
        .accessibilityLabel(MenuSheetCopy.menu)
    }

    private func row(_ item: MenuSheetEntry) -> some View {
        Button {
            onSelect(item.route)
        } label: {
            Text(item.label)
                .font(PDAType.field)
                .foregroundStyle(item.route == .logOut ? PDAColor.foregroundSecondary : PDAColor.foreground)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.vertical, 4)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(item.label)
    }
}
