import Foundation
import XCTest

@testable import PDA

final class CalendarModesTests: XCTestCase {
    private let utc: Calendar = {
        var calendar = Calendar(identifier: .gregorian)
        calendar.timeZone = TimeZone(secondsFromGMT: 0)!
        return calendar
    }()

    private let posix = Locale(identifier: "en_US_POSIX")
    private let wed = iso("2026-09-23T15:00:00Z")

    func test_modes_defaultToMonthAndLabelAgendaAsList() {
        XCTAssertEqual(CalendarMode.allCases.map(\.label), ["month", "week", "day", "list"])
        XCTAssertEqual(AgendaFilter.allCases.map(\.label), ["all", "pda official", "pda club", "community"])
        XCTAssertEqual(CalendarCursor(date: wed).mode, .month)
    }

    func test_week_startsSundayUnlessMondayAndShiftsBySeven() {
        let sunday = calendarWeekDays(containing: wed, weekStart: "sunday", calendar: utc)
        XCTAssertEqual(sunday.map(ymd), [
            "2026-09-20", "2026-09-21", "2026-09-22", "2026-09-23",
            "2026-09-24", "2026-09-25", "2026-09-26",
        ])
        XCTAssertEqual(
            calendarWeekLabel(date: wed, weekStart: "sunday", calendar: utc, locale: posix),
            "week of sep 20"
        )
        let monday = calendarWeekDays(containing: wed, weekStart: "monday", calendar: utc)
        XCTAssertEqual(ymd(monday[0]), "2026-09-21")
        XCTAssertEqual(ymd(monday[6]), "2026-09-27")
        XCTAssertEqual(
            calendarWeekLabel(date: wed, weekStart: "monday", calendar: utc, locale: posix),
            "week of sep 21"
        )

        var cursor = CalendarCursor(date: wed, mode: .week)
        cursor.previousWeek(calendar: utc)
        XCTAssertEqual(ymd(cursor.date), "2026-09-16")
        XCTAssertEqual(cursor.mode, .week)
        cursor = CalendarCursor(date: wed, mode: .week)
        cursor.nextWeek(calendar: utc)
        XCTAssertEqual(ymd(cursor.date), "2026-09-30")
        cursor.goToToday(iso("2026-09-22T08:00:00Z"))
        XCTAssertEqual(ymd(cursor.date), "2026-09-22")
        XCTAssertEqual(cursor.mode, .week)
    }

    func test_narrowWeek_showsTwoChipsAndCountsTheRest() throws {
        let events = try [
            event("late", "Late One", "2026-09-23T18:00:00Z"),
            event("early", "Early One", "2026-09-23T10:00:00Z"),
            event("mid", "Mid One", "2026-09-23T12:00:00Z"),
            event("next", "Next Day", "2026-09-24T09:00:00Z"),
            event("span", "Overnight", "2026-09-22T22:00:00Z", "2026-09-23T01:00:00Z"),
        ]
        let rows = narrowWeekRows(
            events: events, date: wed, weekStart: "sunday", calendar: utc, locale: posix
        )
        let wednesday = rows.first { $0.dayNumber == "23" }
        XCTAssertEqual(wednesday?.weekday, "wed")
        XCTAssertEqual(wednesday?.chips.map(\.id), ["early", "mid"])
        XCTAssertEqual(wednesday?.chips.map(\.time), ["10:00am", "12:00pm"])
        XCTAssertEqual(wednesday?.chips.map(\.title), ["Early One", "Mid One"])
        XCTAssertEqual(wednesday?.overflow, "1 more")
        XCTAssertEqual(rows.first { $0.dayNumber == "22" }?.chips.map(\.id), ["span"])
        XCTAssertEqual(rows.first { $0.dayNumber == "24" }?.chips.map(\.title), ["Next Day"])
        XCTAssertNil(rows.first { $0.dayNumber == "20" }?.overflow)
    }

    func test_day_overlapsTheLocalDayAndFormatsTheRange() throws {
        let events = try [
            event("span", "Overnight", "2026-09-22T22:00:00Z", "2026-09-23T01:00:00Z", location: "Prospect Park"),
            event("same", "Donuts", "2026-09-23T18:00:00Z", "2026-09-23T20:00:00Z", type: "official", description: "come through"),
            event("open", "No End", "2026-09-23T15:00:00Z"),
            event("next", "Thursday", "2026-09-24T09:00:00Z", "2026-09-24T10:00:00Z"),
            event("touch", "Ends At Midnight", "2026-09-22T20:00:00Z", "2026-09-23T00:00:00Z"),
        ]
        let cards = dayEventCards(events: events, day: wed, calendar: utc, locale: posix)
        XCTAssertEqual(cards.map(\.id), ["span", "open", "same"])
        XCTAssertEqual(cards[0].timeRange, "sep 22 10:00pm – sep 23 1:00am")
        XCTAssertEqual(cards[0].location, "Prospect Park")
        XCTAssertNil(cards[0].badge)
        XCTAssertEqual(cards[2].timeRange, "6:00pm – 8:00pm")
        XCTAssertEqual(cards[2].badge, "official")
        XCTAssertEqual(cards[2].description, "come through")
        XCTAssertEqual(cards[1].timeRange, "3:00pm")
        XCTAssertEqual(dayHeaderLabel(date: wed, calendar: utc, locale: posix), "wednesday, sep 23")
        XCTAssertEqual(dayEmptyCopy, "nothing today")
        XCTAssertTrue(dayEventCards(events: [], day: wed, calendar: utc, locale: posix).isEmpty)

        var cursor = CalendarCursor(date: wed, mode: .day)
        cursor.previousDay(calendar: utc)
        XCTAssertEqual(ymd(cursor.date), "2026-09-22")
        cursor.nextDay(calendar: utc)
        cursor.nextDay(calendar: utc)
        XCTAssertEqual(ymd(cursor.date), "2026-09-24")
        cursor.openDay(iso("2026-09-21T00:00:00Z"))
        XCTAssertEqual(cursor.mode, .day)
        XCTAssertEqual(ymd(cursor.date), "2026-09-21")
    }

    func test_agenda_keepsUpcomingAndFiltersByType() throws {
        let now = iso("2026-08-01T14:00:00Z")
        let events = try [
            event("ended", "Morning", "2026-08-01T10:00:00Z", "2026-08-01T11:00:00Z"),
            event("later", "Evening", "2026-08-01T18:00:00Z", "2026-08-01T20:00:00Z", type: "community", location: "The Lot"),
            event("short", "Still Going", "2026-08-01T13:00:00Z"),
            event("gone", "Default Over", "2026-08-01T11:00:00Z"),
            event("club", "Club Night", "2026-08-02T01:00:00Z", "2026-08-03T01:00:00Z", type: "club"),
            event("official", "Meeting", "2026-08-01T16:00:00Z", "2026-08-01T17:00:00Z", type: "official"),
        ]
        let cards = agendaCards(events: events, now: now, filter: .all, calendar: utc, locale: posix)
        XCTAssertEqual(cards.map(\.id), ["short", "official", "later", "club"])
        XCTAssertEqual(cards[2].when, "sat, aug 1 · 6:00pm")
        XCTAssertEqual(cards[2].location, "The Lot")
        XCTAssertNil(cards[2].badge)
        XCTAssertEqual(cards[1].badge, "official")
        XCTAssertEqual(cards[3].when, "sun, aug 2 – mon, aug 3")
        XCTAssertEqual(cards[3].badge, "pda club")
        XCTAssertEqual(
            agendaCards(events: events, now: now, filter: .official, calendar: utc, locale: posix).map(\.id),
            ["official"]
        )
        XCTAssertEqual(
            agendaCards(events: events, now: now, filter: .club, calendar: utc, locale: posix).map(\.id),
            ["club"]
        )
        XCTAssertEqual(
            agendaCards(events: events, now: now, filter: .community, calendar: utc, locale: posix).map(\.id),
            ["short", "later"]
        )
        XCTAssertEqual(agendaEmptyMessage(.all), "nothing on the horizon — pop back later")
        XCTAssertEqual(agendaEmptyMessage(.official), "no pda official events coming up")
        XCTAssertEqual(agendaEmptyMessage(.club), "no pda club events coming up")
        XCTAssertEqual(agendaEmptyMessage(.community), "no community events coming up")
    }

    private func ymd(_ date: Date) -> String {
        let formatter = DateFormatter()
        formatter.locale = posix
        formatter.timeZone = utc.timeZone
        formatter.dateFormat = "yyyy-MM-dd"
        return formatter.string(from: date)
    }

    private func event(
        _ id: String,
        _ title: String,
        _ start: String,
        _ end: String? = nil,
        type: String = "community",
        location: String = "",
        description: String = ""
    ) throws -> Event {
        let endJSON = end.map { "\"\($0)\"" } ?? "null"
        return try Event.decodeJSON("""
        {"id":"\(id)","title":"\(title)","start_datetime":"\(start)","end_datetime":\(endJSON),"event_type":"\(type)","location":"\(location)","description":"\(description)"}
        """)
    }
}

private func iso(_ raw: String) -> Date {
    Event.parseISODate(raw)!
}
