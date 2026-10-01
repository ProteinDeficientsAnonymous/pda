import SwiftUI

enum PaymentConfirmError: Error {
    static let code = "event.payment_confirmation_required"
    case required
}

enum PaymentConfirmCopy {
    static let instructions = "pay the host before you rsvp — then confirm below"
    static let confirm = "yes, i paid"
    static let back = "back"
    static let venmo = "venmo"
    static let cashapp = "cashapp"
    static let required = "confirm you paid before rsvping to this event"
}

func eventRequiresPaymentConfirmation(_ event: Event) -> Bool {
    let price = event.price.trimmingCharacters(in: .whitespacesAndNewlines)
    let hasMethod = [event.venmoLink, event.cashappLink, event.zelleInfo].contains {
        !$0.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }
    return !price.isEmpty && hasMethod
}

func needsPaymentConfirmation(
    event: Event,
    flagOn: Bool,
    status: String,
    alreadyPaid: Bool
) -> Bool {
    flagOn && status == "attending" && !alreadyPaid && eventRequiresPaymentConfirmation(event)
}

func memberRsvpNeedsPayment(event: Event, flagOn: Bool, status: String) -> Bool {
    needsPaymentConfirmation(
        event: event,
        flagOn: flagOn,
        status: status,
        alreadyPaid: event.myPaidConfirmed
    )
}

func rsvpSaveError(_ error: Error) -> String {
    if error is PaymentConfirmError { return PaymentConfirmCopy.required }
    return "couldn't save your rsvp — try again"
}

func formatPaymentPrice(_ price: String) -> String {
    let trimmed = price.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.isEmpty || trimmed.hasPrefix("$") { return trimmed }
    if trimmed.first?.isNumber == true { return "$\(trimmed)" }
    return trimmed
}

func venmoPayURL(_ input: String) -> URL? {
    let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.isEmpty { return nil }
    if trimmed.lowercased().hasPrefix("http://") || trimmed.lowercased().hasPrefix("https://") {
        return URL(string: trimmed)
    }
    let handle = trimmed.hasPrefix("@") ? String(trimmed.dropFirst()) : trimmed
    return URL(string: "https://venmo.com/u/\(handle)")
}

func cashAppPayURL(_ input: String, price: String) -> URL? {
    let trimmed = input.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.isEmpty { return nil }
    let base: String
    if trimmed.lowercased().hasPrefix("http://") || trimmed.lowercased().hasPrefix("https://") {
        base = trimmed
    } else {
        let handle = trimmed.hasPrefix("$") ? String(trimmed.dropFirst()) : trimmed
        base = "https://cash.app/$\(handle)"
    }
    guard let amount = cashAppAmount(price) else { return URL(string: base) }
    return URL(string: "\(base)/\(amount)")
}

func paymentZelleLine(_ info: String) -> String {
    "zelle: \(info)"
}

private func cashAppAmount(_ price: String) -> String? {
    var trimmed = price.trimmingCharacters(in: .whitespacesAndNewlines)
    if trimmed.hasPrefix("$") { trimmed.removeFirst() }
    guard trimmed.range(of: #"^\d+(\.\d{1,2})?$"#, options: .regularExpression) != nil else { return nil }
    return trimmed
}

struct PaymentConfirmStep: View {
    let price: String
    let venmoLink: String
    let cashappLink: String
    let zelleInfo: String
    var busy = false
    var onConfirm: () -> Void
    var onBack: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Text(formatPaymentPrice(price))
                .font(PDAType.control)
                .fontWeight(.medium)
                .foregroundStyle(PDAColor.foreground)
            Text(PaymentConfirmCopy.instructions)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foregroundSecondary)
                .multilineTextAlignment(.center)
            if let url = venmoPayURL(venmoLink) {
                payLink(PaymentConfirmCopy.venmo, url: url)
            }
            if let url = cashAppPayURL(cashappLink, price: price) {
                payLink(PaymentConfirmCopy.cashapp, url: url)
            }
            if !zelleInfo.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                Text(paymentZelleLine(zelleInfo))
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foregroundSecondary)
            }
            PDAButton(PaymentConfirmCopy.confirm, variant: .secondary, action: onConfirm)
                .disabled(busy)
            PDAButton(PaymentConfirmCopy.back, variant: .ghost, action: onBack)
                .disabled(busy)
        }
        .frame(maxWidth: .infinity)
    }

    private func payLink(_ title: String, url: URL) -> some View {
        Link(destination: url) {
            Text(title)
                .font(PDAType.control)
                .foregroundStyle(PDAColor.brandOn)
                .frame(maxWidth: .infinity, minHeight: PDAMetrics.controlHeight)
                .background(PDAColor.brand600, in: RoundedRectangle(cornerRadius: PDARadius.md))
        }
        .disabled(busy)
    }
}
