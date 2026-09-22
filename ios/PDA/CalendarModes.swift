import SwiftUI

enum CalendarMode: String, CaseIterable, Equatable {
    case month, week, day, list

    var label: String { rawValue }
}

enum AgendaFilter: String, CaseIterable, Equatable {
    case all, official, club, community

    var label: String {
        switch self {
        case .all: "all"
        case .official: "pda official"
        case .club: "pda club"
        case .community: "community"
        }
    }
}

struct CalendarCursor: Equatable {
    var mode: CalendarMode = .month
    var date: Date
    var filter: AgendaFilter = .all

    init(date: Date, mode: CalendarMode = .month, filter: AgendaFilter = .all) {
        self.date = date
        self.mode = mode
        self.filter = filter
    }

    mutating func previousWeek(calendar: Calendar) {
        date = calendarShift(date, days: -7, calendar: calendar)
    }

    mutating func nextWeek(calendar: Calendar) {
        date = calendarShift(date, days: 7, calendar: calendar)
    }

    mutating func previousDay(calendar: Calendar) {
        date = calendarShift(date, days: -1, calendar: calendar)
    }

    mutating func nextDay(calendar: Calendar) {
        date = calendarShift(date, days: 1, calendar: calendar)
    }

    mutating func goToToday(_ now: Date) {
        date = now
    }

    mutating func openDay(_ day: Date) {
        date = day
        mode = .day
    }
}

struct WeekChip: Equatable {
    let id: String
    let time: String
    let title: String
}

struct NarrowWeekRow: Equatable {
    let weekday: String
    let dayNumber: String
    let isToday: Bool
    let chips: [WeekChip]
    let overflow: String?
}

struct DayEventCard: Equatable {
    let id: String
    let title: String
    let badge: String?
    let timeRange: String
    let location: String
    let description: String
}

struct AgendaCard: Equatable {
    let id: String
    let title: String
    let badge: String?
    let when: String
    let location: String
}

let dayEmptyCopy = "nothing today"

func calendarShift(_ date: Date, days: Int, calendar: Calendar) -> Date {
    calendar.date(byAdding: .day, value: days, to: date)!
}

func calendarWeekDays(containing date: Date, weekStart: String, calendar: Calendar) -> [Date] {
    var cal = calendar
    cal.firstWeekday = weekStart == "monday" ? 2 : 1
    let start = cal.dateInterval(of: .weekOfYear, for: date)!.start
    return (0 ..< 7).map { cal.date(byAdding: .day, value: $0, to: start)! }
}

func calendarWeekLabel(date: Date, weekStart: String, calendar: Calendar, locale: Locale) -> String {
    let start = calendarWeekDays(containing: date, weekStart: weekStart, calendar: calendar)[0]
    return "week of \(calendarStamp(start, "MMM d", calendar: calendar, locale: locale))"
}

func narrowWeekRows(
    events: [Event],
    date: Date,
    weekStart: String,
    calendar: Calendar,
    locale: Locale,
    now: Date = Date()
) -> [NarrowWeekRow] {
    calendarWeekDays(containing: date, weekStart: weekStart, calendar: calendar).map { day in
        let sorted = events
            .filter { event in
                guard let start = event.startDatetime else { return false }
                return calendar.isDate(start, inSameDayAs: day)
            }
            .sorted { ($0.startDatetime ?? .distantFuture) < ($1.startDatetime ?? .distantFuture) }
        let visible = sorted.prefix(2)
        let extra = sorted.count - visible.count
        return NarrowWeekRow(
            weekday: calendarStamp(day, "EEE", calendar: calendar, locale: locale),
            dayNumber: calendarStamp(day, "d", calendar: calendar, locale: locale),
            isToday: calendar.isDate(day, inSameDayAs: now),
            chips: visible.map { event in
                WeekChip(
                    id: event.id,
                    time: event.startDatetime.map {
                        calendarStamp($0, "h:mma", calendar: calendar, locale: locale)
                    } ?? "",
                    title: event.title
                )
            },
            overflow: extra > 0 ? "\(extra) more" : nil
        )
    }
}

func dayHeaderLabel(date: Date, calendar: Calendar, locale: Locale) -> String {
    calendarStamp(date, "EEEE, MMM d", calendar: calendar, locale: locale)
}

func dayEventCards(events: [Event], day: Date, calendar: Calendar, locale: Locale) -> [DayEventCard] {
    let dayStart = calendar.startOfDay(for: day)
    let dayEnd = calendar.date(byAdding: .day, value: 1, to: dayStart)!
    return events
        .filter { event in
            guard let start = event.startDatetime else { return false }
            let end = event.endDatetime ?? start.addingTimeInterval(60)
            return start < dayEnd && end > dayStart
        }
        .sorted { ($0.startDatetime ?? .distantFuture) < ($1.startDatetime ?? .distantFuture) }
        .map { event in
            DayEventCard(
                id: event.id,
                title: event.title,
                badge: calendarTypeBadge(event),
                timeRange: dayTimeRange(event, calendar: calendar, locale: locale),
                location: event.location,
                description: event.description
            )
        }
}

func agendaCards(
    events: [Event],
    now: Date,
    filter: AgendaFilter,
    calendar: Calendar,
    locale: Locale
) -> [AgendaCard] {
    events
        .filter { event in
            guard let start = event.startDatetime else { return false }
            let end = event.endDatetime ?? start.addingTimeInterval(2 * 60 * 60)
            guard end >= now else { return false }
            if filter == .all { return true }
            return event.eventType == filter.rawValue
        }
        .sorted { ($0.startDatetime ?? .distantFuture) < ($1.startDatetime ?? .distantFuture) }
        .map { event in
            AgendaCard(
                id: event.id,
                title: event.title,
                badge: calendarTypeBadge(event),
                when: agendaWhen(event, calendar: calendar, locale: locale),
                location: event.location
            )
        }
}

func agendaEmptyMessage(_ filter: AgendaFilter) -> String {
    switch filter {
    case .official: "no pda official events coming up"
    case .club: "no pda club events coming up"
    case .community: "no community events coming up"
    case .all: "nothing on the horizon — pop back later"
    }
}

private func calendarTypeBadge(_ event: Event) -> String? {
    guard event.eventType == "official" || event.eventType == "club" else { return nil }
    return eventBadgeLabel(status: event.status, eventType: event.eventType, visibility: event.visibility)
}

private func dayTimeRange(_ event: Event, calendar: Calendar, locale: Locale) -> String {
    guard let start = event.startDatetime else { return "" }
    let startTime = calendarStamp(start, "h:mma", calendar: calendar, locale: locale)
    guard let end = event.endDatetime else { return startTime }
    let endTime = calendarStamp(end, "h:mma", calendar: calendar, locale: locale)
    if calendar.isDate(start, inSameDayAs: end) {
        return "\(startTime) – \(endTime)"
    }
    let startDay = calendarStamp(start, "MMM d", calendar: calendar, locale: locale)
    let endDay = calendarStamp(end, "MMM d", calendar: calendar, locale: locale)
    return "\(startDay) \(startTime) – \(endDay) \(endTime)"
}

private func agendaWhen(_ event: Event, calendar: Calendar, locale: Locale) -> String {
    guard let start = event.startDatetime else { return "" }
    let startDate = calendarStamp(start, "EEE, MMM d", calendar: calendar, locale: locale)
    let startTime = calendarStamp(start, "h:mma", calendar: calendar, locale: locale)
    guard let end = event.endDatetime else { return "\(startDate) · \(startTime)" }
    if calendar.isDate(start, inSameDayAs: end) { return "\(startDate) · \(startTime)" }
    let endDate = calendarStamp(end, "EEE, MMM d", calendar: calendar, locale: locale)
    return "\(startDate) – \(endDate)"
}

private func calendarStamp(_ date: Date, _ format: String, calendar: Calendar, locale: Locale) -> String {
    let formatter = DateFormatter()
    formatter.locale = locale
    formatter.timeZone = calendar.timeZone
    formatter.dateFormat = format
    return formatter.string(from: date).lowercased()
}

struct CalendarBrowser: View {
    let events: [Event]
    let weekStart: String
    @State private var cursor = CalendarCursor(date: Date())

    private var calendar: Calendar { .current }
    private var locale: Locale { .current }

    var body: some View {
        VStack(spacing: 8) {
            Picker("calendar view", selection: $cursor.mode) {
                ForEach(CalendarMode.allCases, id: \.self) { mode in
                    Text(mode.label).tag(mode)
                }
            }
            .pickerStyle(.segmented)
            .accessibilityLabel("calendar view")
            .padding(.horizontal, 16)
            .padding(.top, 8)

            switch cursor.mode {
            case .month:
                monthBody
            case .week:
                weekBody
            case .day:
                dayBody
            case .list:
                listBody
            }
        }
    }

    @ViewBuilder
    private var monthBody: some View {
        if events.isEmpty {
            ContentUnavailableView("nothing on the horizon — pop back later", systemImage: "leaf")
        } else {
            List(events) { event in
                NavigationLink(value: event) {
                    EventRow(event: event)
                }
            }
            .listStyle(.plain)
        }
    }

    private var weekBody: some View {
        VStack(spacing: 8) {
            modeToolbar(
                label: calendarWeekLabel(
                    date: cursor.date, weekStart: weekStart, calendar: calendar, locale: locale
                ),
                previousLabel: "previous week",
                nextLabel: "next week",
                previous: { cursor.previousWeek(calendar: calendar) },
                next: { cursor.nextWeek(calendar: calendar) }
            )
            let rows = narrowWeekRows(
                events: events,
                date: cursor.date,
                weekStart: weekStart,
                calendar: calendar,
                locale: locale
            )
            ScrollView {
                VStack(spacing: 0) {
                    ForEach(rows, id: \.dayNumber) { row in
                        weekRow(row)
                    }
                }
                .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.md))
                .overlay(
                    RoundedRectangle(cornerRadius: PDARadius.md)
                        .stroke(PDAColor.border, lineWidth: 1)
                )
                .padding(.horizontal, 16)
            }
        }
    }

    private func weekRow(_ row: NarrowWeekRow) -> some View {
        HStack(alignment: .center, spacing: 8) {
            VStack(spacing: 0) {
                Text(row.weekday).font(PDAType.control)
                Text(row.dayNumber).font(PDAType.field).fontWeight(.medium)
            }
            .foregroundStyle(row.isToday ? PDAColor.brandOn : PDAColor.foregroundSecondary)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(row.isToday ? PDAColor.brand600 : Color.clear, in: RoundedRectangle(cornerRadius: PDARadius.md))
            .frame(width: 56)
            VStack(alignment: .leading, spacing: 4) {
                ForEach(row.chips, id: \.id) { chip in
                    NavigationLink(value: events.first { $0.id == chip.id }!) {
                        HStack(spacing: 8) {
                            if !chip.time.isEmpty {
                                Text(chip.time).font(PDAType.control)
                            }
                            Text(chip.title).font(PDAType.control).lineLimit(1)
                        }
                        .foregroundStyle(PDAColor.foreground)
                    }
                }
                if let overflow = row.overflow {
                    Text(overflow)
                        .font(PDAType.control)
                        .foregroundStyle(PDAColor.brand700)
                }
            }
            Spacer(minLength: 0)
        }
        .padding(.vertical, 6)
        .padding(.trailing, 8)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(row.weekday) \(row.dayNumber)")
    }

    private var dayBody: some View {
        let cards = dayEventCards(events: events, day: cursor.date, calendar: calendar, locale: locale)
        return VStack(spacing: 8) {
            modeToolbar(
                label: dayHeaderLabel(date: cursor.date, calendar: calendar, locale: locale),
                previousLabel: "previous day",
                nextLabel: "next day",
                previous: { cursor.previousDay(calendar: calendar) },
                next: { cursor.nextDay(calendar: calendar) }
            )
            if cards.isEmpty {
                calendarEmpty(dayEmptyCopy)
            } else {
                ScrollView {
                    VStack(spacing: 10) {
                        ForEach(cards, id: \.id) { card in
                            NavigationLink(value: events.first { $0.id == card.id }!) {
                                dayCard(card)
                            }
                        }
                    }
                    .padding(.horizontal, 16)
                }
            }
        }
    }

    private func dayCard(_ card: DayEventCard) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(card.title).font(PDAType.field).fontWeight(.medium).foregroundStyle(PDAColor.foreground)
            if let badge = card.badge {
                Text(badge)
                    .font(PDAType.control)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(PDAColor.surfaceDim, in: Capsule())
            }
            if !card.timeRange.isEmpty {
                Text(card.timeRange).font(PDAType.control).foregroundStyle(PDAColor.foregroundSecondary)
            }
            if !card.location.isEmpty {
                Text(card.location).font(PDAType.control).foregroundStyle(PDAColor.foregroundSecondary)
            }
            if !card.description.isEmpty {
                Text(card.description)
                    .font(PDAType.control)
                    .foregroundStyle(PDAColor.foregroundSecondary)
                    .lineLimit(2)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.md))
        .accessibilityLabel(card.title)
    }

    private var listBody: some View {
        let cards = agendaCards(
            events: events, now: Date(), filter: cursor.filter, calendar: calendar, locale: locale
        )
        return VStack(spacing: 8) {
            Picker("event type filter", selection: $cursor.filter) {
                ForEach(AgendaFilter.allCases, id: \.self) { filter in
                    Text(filter.label).tag(filter)
                }
            }
            .pickerStyle(.segmented)
            .accessibilityLabel("event type filter")
            .padding(.horizontal, 16)
            if cards.isEmpty {
                calendarEmpty(agendaEmptyMessage(cursor.filter))
            } else {
                ScrollView {
                    VStack(spacing: 10) {
                        ForEach(cards, id: \.id) { card in
                            NavigationLink(value: events.first { $0.id == card.id }!) {
                                agendaCard(card)
                            }
                        }
                    }
                    .padding(.horizontal, 16)
                }
            }
        }
    }

    private func agendaCard(_ card: AgendaCard) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(card.title).font(PDAType.field).fontWeight(.medium).foregroundStyle(PDAColor.foreground)
            if let badge = card.badge {
                Text(badge)
                    .font(PDAType.control)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 3)
                    .background(PDAColor.surfaceDim, in: Capsule())
            }
            if !card.when.isEmpty {
                Text(card.when).font(PDAType.control).foregroundStyle(PDAColor.foregroundSecondary)
            }
            if !card.location.isEmpty {
                Text(card.location).font(PDAType.control).foregroundStyle(PDAColor.foregroundSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(12)
        .background(PDAColor.surface, in: RoundedRectangle(cornerRadius: PDARadius.md))
        .accessibilityLabel(card.title)
    }

    private func modeToolbar(
        label: String,
        previousLabel: String,
        nextLabel: String,
        previous: @escaping () -> Void,
        next: @escaping () -> Void
    ) -> some View {
        ZStack {
            HStack {
                PDAButton("today", variant: .ghost) { cursor.goToToday(Date()) }
                    .accessibilityLabel("go to today")
                Spacer()
            }
            HStack(spacing: 4) {
                PDAButton("‹", variant: .ghost, action: previous)
                    .accessibilityLabel(previousLabel)
                Text(label)
                    .font(PDAType.control)
                    .fontWeight(.medium)
                    .foregroundStyle(PDAColor.foreground)
                PDAButton("›", variant: .ghost, action: next)
                    .accessibilityLabel(nextLabel)
            }
        }
        .padding(.horizontal, 16)
    }

    private func calendarEmpty(_ message: String) -> some View {
        VStack(spacing: 12) {
            Text("🌿").font(.system(size: 36))
            Text(message).font(PDAType.control).foregroundStyle(PDAColor.muted)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
