import XCTest

@testable import PDA

final class AttendanceReportTests: XCTestCase {
    private let base = URL(string: "https://pda.test")!

    override func tearDown() {
        MockHTTP.handler = nil
        super.tearDown()
    }

    func test_attendanceReportURL_keepsTrailingSlash() {
        let url = attendanceReportURL(base: base)
        XCTAssertEqual(url.absoluteString, "https://pda.test/api/community/events/attendance-report/")
        XCTAssertNil(url.query)
    }

    func test_attendanceReport_getsRowsWithBearer() async throws {
        let tokens = MemoryTokenStore()
        try tokens.save("access-jwt")
        MockHTTP.handler = { request in
            XCTAssertEqual(request.httpMethod, "GET")
            XCTAssertEqual(routePath(request.url), "/api/community/events/attendance-report/")
            XCTAssertNil(request.url?.query)
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer access-jwt")
            return MockHTTP.json(200, reportJSON(events: [
                rowJSON(id: "e1", title: "Potluck", attended: 4, noShow: 1),
            ]))
        }
        let report = try await makeClient(tokens).attendanceReport()
        XCTAssertEqual(report.events.map(\.eventId), ["e1"])
        XCTAssertEqual(report.events[0].title, "Potluck")
        XCTAssertEqual(report.events[0].attendedCount, 4)
        XCTAssertEqual(report.events[0].noShowCount, 1)
        XCTAssertEqual(report.officialNoShowCount, 1)
        XCTAssertEqual(report.clubNoShowCount, 0)
    }

    func test_attendanceReport_403WithoutManageEvents() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        do {
            _ = try await makeClient().attendanceReport()
            XCTFail("403 should not return the report")
        } catch AttendanceReportError.forbidden {
        } catch {
            XCTFail("wrong error \(error)")
        }
    }

    func test_attendanceModel_forbiddenShowsExplanationNotList() async {
        MockHTTP.handler = { _ in
            MockHTTP.json(403, ["detail": [["code": "perm.denied"]]])
        }
        let model = AttendanceReportModel(client: makeClient())
        await model.load()
        XCTAssertTrue(model.forbidden)
        XCTAssertTrue(model.rows.isEmpty)
        XCTAssertEqual(model.explanationTitle, AttendanceReportCopy.forbiddenTitle)
        XCTAssertEqual(model.explanationBody, AttendanceReportCopy.forbiddenBody)
    }

    func test_attendanceRowsLinkOnlyWhenHostReportFlagOn() {
        XCTAssertFalse(attendanceRowsLink(flags: [:]))
        XCTAssertFalse(attendanceRowsLink(flags: ["host_attendance_report": false]))
        XCTAssertTrue(attendanceRowsLink(flags: ["host_attendance_report": true]))
    }

    func test_attendanceModel_flagOffKeepsListButNotLinks() async {
        MockHTTP.handler = { request in
            if routePath(request.url) == "/api/community/feature-flags/" {
                return MockHTTP.json(200, ["flags": ["host_attendance_report": false]])
            }
            return MockHTTP.json(200, reportJSON(events: [
                rowJSON(id: "e1", title: "Potluck", attended: 1, noShow: 0),
            ]))
        }
        let model = AttendanceReportModel(client: makeClient())
        await model.load()
        XCTAssertEqual(model.rows.map(\.eventId), ["e1"])
        XCTAssertFalse(model.linksEnabled)
        XCTAssertFalse(model.forbidden)
    }

    func test_attendanceEventWhen_emptyStartIsTbd() {
        let row = AttendanceEventRow(
            eventId: "e1",
            title: "Potluck",
            eventType: "official",
            startDatetime: "",
            attendedCount: 0,
            noShowCount: 0,
            goingCount: 0
        )
        XCTAssertEqual(attendanceEventWhen(row), AttendanceReportCopy.dateTbd)
        XCTAssertEqual(attendanceStat(AttendanceReportCopy.attended, 4), "4 attended")
        XCTAssertEqual(attendanceStat(AttendanceReportCopy.noShow, 1), "1 no-show")
    }

    func test_attendanceTile_opensListOnly() throws {
        let tiles = adminHubTiles(for: try user(permissions: [
            "manage_events",
            "manage_documents",
        ]))
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .attendance }.map(\.id), ["attendance"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .events }.map(\.id), ["events"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == .flaggedEvents }.map(\.id), ["flagged-events"])
        XCTAssertEqual(tiles.filter { adminHubDestination(for: $0) == nil }.map(\.id), ["docs"])
    }

    func test_attendanceReportCopy_isLowercase() {
        let blobs = [
            AttendanceReportCopy.title,
            AttendanceReportCopy.subtitle,
            AttendanceReportCopy.loading,
            AttendanceReportCopy.error,
            AttendanceReportCopy.empty,
            AttendanceReportCopy.attended,
            AttendanceReportCopy.noShow,
            AttendanceReportCopy.dateTbd,
            AttendanceReportCopy.forbiddenTitle,
            AttendanceReportCopy.forbiddenBody,
        ]
        XCTAssertEqual(AttendanceReportCopy.title, "attendance")
        XCTAssertEqual(AttendanceReportCopy.error, "couldn't load attendance — try refreshing")
        XCTAssertEqual(AttendanceReportCopy.empty, "no attendance marked yet 🌿")
        XCTAssertEqual(AttendanceReportCopy.dateTbd, "date tbd")
        for text in blobs {
            XCTAssertEqual(text, text.lowercased(), text)
        }
    }

    private func makeClient(_ tokens: MemoryTokenStore? = nil) -> EventsClient {
        EventsClient(baseURL: base, session: MockHTTP.session(), tokens: tokens)
    }

    private func user(permissions: [String]) throws -> SessionUser {
        let payload: [String: Any] = [
            "id": "user-1",
            "is_member": true,
            "permissions": permissions,
            "roles": [],
        ]
        return try JSONDecoder().decode(SessionUser.self, from: JSONSerialization.data(withJSONObject: payload))
    }
}

private func rowJSON(id: String, title: String, attended: Int, noShow: Int) -> [String: Any] {
    [
        "event_id": id,
        "title": title,
        "event_type": "official",
        "start_datetime": "2026-03-01T18:00:00Z",
        "attended_count": attended,
        "no_show_count": noShow,
        "going_count": 5,
    ]
}

private func reportJSON(events: [[String: Any]]) -> [String: Any] {
    [
        "events": events,
        "official_no_show_count": 1,
        "club_no_show_count": 0,
    ]
}

private func routePath(_ url: URL?) -> String {
    guard let url else { return "" }
    let path = url.path
    return path.hasSuffix("/") ? path : path + "/"
}
