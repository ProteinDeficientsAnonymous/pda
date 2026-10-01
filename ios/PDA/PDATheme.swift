import SwiftUI
import UIKit

struct PDAHex: Equatable {
    var light: String
    var dark: String
}

enum PDAPalette {
    static let background = PDAHex(light: "#f7fbf1", dark: "#10140f")
    static let foreground = PDAHex(light: "#191d17", dark: "#e0e4db")
    static let foregroundSecondary = PDAHex(light: "#404040", dark: "#d4d4d4")
    static let foregroundTertiary = PDAHex(light: "#525252", dark: "#a3a3a3")
    static let surface = PDAHex(light: "#ffffff", dark: "#0b0f0a")
    static let surfaceDim = PDAHex(light: "#e6e9e0", dark: "#272b25")
    static let surfaceActive = PDAHex(light: "#e0e4db", dark: "#323630")
    static let surfaceRaised = PDAHex(light: "#e5e5e5", dark: "#404040")
    static let border = PDAHex(light: "#c2c9bd", dark: "#424940")
    static let borderStrong = PDAHex(light: "#72796f", dark: "#8c9388")
    static let muted = PDAHex(light: "#424940", dark: "#c2c9bd")
    static let mutedForeground = PDAHex(light: "#72796f", dark: "#8c9388")
    static let accent = PDAHex(light: "#2d322c", dark: "#e0e4db")
    static let accentForeground = PDAHex(light: "#eff2e9", dark: "#2d322c")
    static let toggleOff = PDAHex(light: "#d4d4d4", dark: "#525252")
    static let destructive = PDAHex(light: "#dc2626", dark: "#f87171")
    static let destructiveSubtle = PDAHex(light: "#fef2f2", dark: "rgba(127, 29, 29, 0.3)")
    static let destructiveBorder = PDAHex(light: "#ef4444", dark: "#f87171")
    static let success = PDAHex(light: "#166534", dark: "#86efac")
    static let successSubtle = PDAHex(light: "#dcfce7", dark: "rgba(20, 83, 45, 0.3)")
    static let warning = PDAHex(light: "#92400e", dark: "#fcd34d")
    static let warningSubtle = PDAHex(light: "#fef3c7", dark: "rgba(120, 53, 15, 0.3)")
    static let info = PDAHex(light: "#1e3a5f", dark: "#93c5fd")
    static let infoSubtle = PDAHex(light: "#dbeafe", dark: "rgba(30, 58, 95, 0.3)")
    static let highlight = PDAHex(light: "#3b0764", dark: "#d8b4fe")
    static let highlightSubtle = PDAHex(light: "#f3e8ff", dark: "rgba(59, 7, 100, 0.3)")
    static let positive = PDAHex(light: "#065f46", dark: "#6ee7b7")
    static let positiveSubtle = PDAHex(light: "#d1fae5", dark: "rgba(6, 95, 70, 0.3)")
    static let positiveBorder = PDAHex(light: "#6ee7b7", dark: "#065f46")
    static let brand50 = PDAHex(light: "#bcf0b4", dark: "#0a390f")
    static let brand100 = PDAHex(light: "#a1d39a", dark: "#245024")
    static let brand200 = PDAHex(light: "#82b87c", dark: "#3c6939")
    static let brand300 = PDAHex(light: "#5a9a55", dark: "#5a9a55")
    static let brand400 = PDAHex(light: "#4a8346", dark: "#82b87c")
    static let brand500 = PDAHex(light: "#3c6939", dark: "#a1d39a")
    static let brand600 = PDAHex(light: "#3c6939", dark: "#a1d39a")
    static let brand700 = PDAHex(light: "#245024", dark: "#bcf0b4")
    static let brand800 = PDAHex(light: "#1c4e1f", dark: "#a1d39a")
    static let brand900 = PDAHex(light: "#0a390f", dark: "#82b87c")
    static let brandOn = PDAHex(light: "#ffffff", dark: "#0a390f")
    static let evtCommunityBg = PDAHex(light: "#cce8e4", dark: "#103028")
    static let evtCommunityFg = PDAHex(light: "#0a3c34", dark: "#a8e0d8")
    static let evtOfficialBg = PDAHex(light: "#d0e8ff", dark: "#1a3050")
    static let evtOfficialFg = PDAHex(light: "#0b2a4a", dark: "#b0d4ff")
    static let evtClubBg = PDAHex(light: "#f5d0e0", dark: "#3d1028")
    static let evtClubFg = PDAHex(light: "#5c1a3a", dark: "#f0b0d0")
    static let evtMembersBg = PDAHex(light: "#ffe0b2", dark: "#3d2810")
    static let evtMembersFg = PDAHex(light: "#4a2808", dark: "#ffd6a0")
    static let evtInviteBg = PDAHex(light: "#e0d0f0", dark: "#201040")
    static let evtInviteFg = PDAHex(light: "#2a104a", dark: "#d0b8ff")
    static let evtCancelledBg = PDAHex(light: "#ecefe6", dark: "#1d211b")
    static let evtCancelledFg = PDAHex(light: "#72796f", dark: "#8c9388")
    static let evtCancelledBorder = PDAHex(light: "#8c9388", dark: "#4b5563")
}

enum PDARadius {
    static let sm: CGFloat = 6
    static let md: CGFloat = 12
    static let lg: CGFloat = 20
}

enum PDAType {
    static let control = Font.system(size: 14, weight: .medium)
    static let field = Font.system(size: 16)
}

enum PDAMetrics {
    static let controlHeight: CGFloat = 40
    static let buttonPaddingX: CGFloat = 16
    static let fieldPaddingX: CGFloat = 12
}

enum PDAColor {
    static let background = color(PDAPalette.background)
    static let foreground = color(PDAPalette.foreground)
    static let foregroundSecondary = color(PDAPalette.foregroundSecondary)
    static let foregroundTertiary = color(PDAPalette.foregroundTertiary)
    static let surface = color(PDAPalette.surface)
    static let surfaceDim = color(PDAPalette.surfaceDim)
    static let surfaceActive = color(PDAPalette.surfaceActive)
    static let surfaceRaised = color(PDAPalette.surfaceRaised)
    static let border = color(PDAPalette.border)
    static let borderStrong = color(PDAPalette.borderStrong)
    static let muted = color(PDAPalette.muted)
    static let mutedForeground = color(PDAPalette.mutedForeground)
    static let accent = color(PDAPalette.accent)
    static let accentForeground = color(PDAPalette.accentForeground)
    static let toggleOff = color(PDAPalette.toggleOff)
    static let destructive = color(PDAPalette.destructive)
    static let destructiveSubtle = color(PDAPalette.destructiveSubtle)
    static let destructiveBorder = color(PDAPalette.destructiveBorder)
    static let success = color(PDAPalette.success)
    static let successSubtle = color(PDAPalette.successSubtle)
    static let warning = color(PDAPalette.warning)
    static let warningSubtle = color(PDAPalette.warningSubtle)
    static let info = color(PDAPalette.info)
    static let infoSubtle = color(PDAPalette.infoSubtle)
    static let highlight = color(PDAPalette.highlight)
    static let highlightSubtle = color(PDAPalette.highlightSubtle)
    static let positive = color(PDAPalette.positive)
    static let positiveSubtle = color(PDAPalette.positiveSubtle)
    static let positiveBorder = color(PDAPalette.positiveBorder)
    static let brand50 = color(PDAPalette.brand50)
    static let brand100 = color(PDAPalette.brand100)
    static let brand200 = color(PDAPalette.brand200)
    static let brand300 = color(PDAPalette.brand300)
    static let brand400 = color(PDAPalette.brand400)
    static let brand500 = color(PDAPalette.brand500)
    static let brand600 = color(PDAPalette.brand600)
    static let brand700 = color(PDAPalette.brand700)
    static let brand800 = color(PDAPalette.brand800)
    static let brand900 = color(PDAPalette.brand900)
    static let brandOn = color(PDAPalette.brandOn)

    static func color(_ token: PDAHex) -> Color {
        Color(uiColor: UIColor { traits in
            let hex = traits.userInterfaceStyle == .dark ? token.dark : token.light
            return UIColor(pda: hex)
        })
    }
}

struct PDAButton: View {
    enum Variant { case primary, secondary, ghost }

    private let title: String
    private let variant: Variant
    private let action: () -> Void

    init(_ title: String, variant: Variant = .primary, action: @escaping () -> Void) {
        self.title = title
        self.variant = variant
        self.action = action
    }

    var body: some View {
        Button(action: action) {
            Text(title)
        }
        .buttonStyle(PDAButtonStyle(variant: variant))
    }
}

struct PDATextField: View {
    private let label: String
    @Binding private var text: String
    private let axis: Axis
    private let capitalization: TextInputAutocapitalization
    private let disableAutocorrection: Bool
    private let keyboard: UIKeyboardType
    private let contentType: UITextContentType?
    private let identifier: String?
    private let lineLimit: Int?
    private let reserveLineSpace: Bool
    @FocusState private var focused: Bool

    init(
        _ label: String,
        text: Binding<String>,
        axis: Axis = .horizontal,
        capitalization: TextInputAutocapitalization = .sentences,
        disableAutocorrection: Bool = false,
        keyboard: UIKeyboardType = .default,
        contentType: UITextContentType? = nil,
        identifier: String? = nil,
        lineLimit: Int? = nil,
        reserveLineSpace: Bool = false
    ) {
        self.label = label
        _text = text
        self.axis = axis
        self.capitalization = capitalization
        self.disableAutocorrection = disableAutocorrection
        self.keyboard = keyboard
        self.contentType = contentType
        self.identifier = identifier
        self.lineLimit = lineLimit
        self.reserveLineSpace = reserveLineSpace
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
                .accessibilityHidden(true)
            field
                .font(PDAType.field)
                .foregroundStyle(PDAColor.foreground)
                .textInputAutocapitalization(capitalization)
                .autocorrectionDisabled(disableAutocorrection)
                .keyboardType(keyboard)
                .textContentType(contentType)
                .focused($focused)
                .padding(.horizontal, PDAMetrics.fieldPaddingX)
                .frame(minHeight: PDAMetrics.controlHeight)
                .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.md))
                .overlay {
                    RoundedRectangle(cornerRadius: PDARadius.md)
                        .strokeBorder(PDAColor.borderStrong, lineWidth: 1)
                }
                .overlay {
                    if focused {
                        RoundedRectangle(cornerRadius: PDARadius.md)
                            .stroke(PDAColor.brand200, lineWidth: 2)
                    }
                }
                .accessibilityLabel(label)
                .modifier(PDAFieldIdentifier(identifier: identifier))
        }
    }

    @ViewBuilder
    private var field: some View {
        if let lineLimit {
            TextField("", text: $text, axis: axis)
                .lineLimit(lineLimit, reservesSpace: reserveLineSpace)
        } else {
            TextField("", text: $text, axis: axis)
        }
    }
}

private struct PDAButtonStyle: ButtonStyle {
    var variant: PDAButton.Variant
    @Environment(\.isEnabled) private var isEnabled

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(PDAType.control)
            .foregroundStyle(labelColor)
            .padding(.horizontal, PDAMetrics.buttonPaddingX)
            .frame(minHeight: PDAMetrics.controlHeight)
            .background(fill(pressed: configuration.isPressed), in: RoundedRectangle(cornerRadius: PDARadius.md))
            .overlay {
                if variant == .secondary {
                    RoundedRectangle(cornerRadius: PDARadius.md)
                        .strokeBorder(PDAColor.borderStrong, lineWidth: 1)
                }
            }
            .opacity(variant == .primary || isEnabled ? 1 : 0.5)
    }

    private var labelColor: Color {
        switch variant {
        case .primary: PDAColor.brandOn
        case .secondary: PDAColor.foreground
        case .ghost: PDAColor.foregroundSecondary
        }
    }

    private func fill(pressed: Bool) -> Color {
        switch variant {
        case .primary:
            if !isEnabled { return PDAColor.toggleOff }
            return pressed ? PDAColor.brand700 : PDAColor.brand600
        case .secondary:
            return pressed ? PDAColor.background : PDAColor.surface
        case .ghost:
            return pressed ? PDAColor.surfaceDim : .clear
        }
    }
}

private struct PDAFieldIdentifier: ViewModifier {
    var identifier: String?

    func body(content: Content) -> some View {
        if let identifier {
            content.accessibilityIdentifier(identifier)
        } else {
            content
        }
    }
}

private extension UIColor {
    convenience init(pda raw: String) {
        let trimmed = raw.trimmingCharacters(in: .whitespaces)
        if trimmed.hasPrefix("rgba") {
            let parts = trimmed
                .dropFirst(5)
                .dropLast()
                .split(separator: ",")
                .map { $0.trimmingCharacters(in: .whitespaces) }
            precondition(parts.count == 4, "bad theme color \(raw)")
            let channels = parts.prefix(3).map { channel -> CGFloat in
                guard let value = Double(channel) else { preconditionFailure("bad theme color \(raw)") }
                return CGFloat(value) / 255
            }
            guard let alpha = Double(parts[3]) else { preconditionFailure("bad theme color \(raw)") }
            self.init(red: channels[0], green: channels[1], blue: channels[2], alpha: CGFloat(alpha))
            return
        }
        var hex = trimmed
        if hex.hasPrefix("#") { hex.removeFirst() }
        precondition(hex.count == 6, "bad theme color \(raw)")
        var value: UInt64 = 0
        precondition(Scanner(string: hex).scanHexInt64(&value), "bad theme color \(raw)")
        self.init(
            red: CGFloat((value >> 16) & 0xff) / 255,
            green: CGFloat((value >> 8) & 0xff) / 255,
            blue: CGFloat(value & 0xff) / 255,
            alpha: 1
        )
    }
}
