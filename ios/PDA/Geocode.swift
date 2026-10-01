import SwiftUI

enum GeocodeCopy {
    static let label = "location"
    static let placeholder = "search an address or place"
}

struct GeocodePlace: Equatable, Identifiable {
    var name: String
    var subtitle: String?
    var fullAddress: String
    var latitude: Double
    var longitude: Double
    var id: String { "\(latitude),\(longitude),\(fullAddress)" }
}

func geocodeResults(from payload: [String: Any]) -> [GeocodePlace] {
    let features = payload["features"] as? [[String: Any]] ?? []
    return features.compactMap(geocodePlace).filter { !$0.name.isEmpty }
}

func geocodePlace(_ feature: [String: Any]) -> GeocodePlace? {
    let geometry = feature["geometry"] as? [String: Any]
    let rawCoords = geometry?["coordinates"]
    let coords: [Double] = (rawCoords as? [Double])
        ?? ((rawCoords as? [Any])?.compactMap { ($0 as? NSNumber)?.doubleValue } ?? [])
    guard coords.count >= 2 else { return nil }
    let lon = coords[0]
    let lat = coords[1]
    let props = feature["properties"] as? [String: Any] ?? [:]
    let placeName = props["name"] as? String ?? ""
    let street = props["street"] as? String
    let house = props["housenumber"] as? String
    let streetAddress: String? = {
        if let house, let street, !house.isEmpty, !street.isEmpty { return "\(house) \(street)" }
        return street
    }()
    let name = placeName.isEmpty ? (streetAddress ?? "") : placeName
    let subtitle = (!placeName.isEmpty && streetAddress != nil) ? streetAddress : (props["city"] as? String)
    let city = props["city"] as? String
    let cityLabel = city == "New York" ? "ny" : city
    var parts: [String] = []
    if !placeName.isEmpty { parts.append(placeName) }
    if let streetAddress, streetAddress != placeName { parts.append(streetAddress) }
    if let cityLabel, cityLabel != placeName, cityLabel != streetAddress { parts.append(cityLabel) }
    return GeocodePlace(
        name: name,
        subtitle: subtitle,
        fullAddress: parts.joined(separator: ", ").lowercased(),
        latitude: lat,
        longitude: lon
    )
}

func geocodeURL(base: URL, query: String) -> URL {
    var comps = URLComponents(
        url: URL(string: "/api/community/geocode/", relativeTo: base)!.absoluteURL,
        resolvingAgainstBaseURL: false
    )!
    comps.queryItems = [
        URLQueryItem(name: "q", value: query),
        URLQueryItem(name: "limit", value: "5"),
    ]
    return comps.url!
}

extension EventsClient {
    func geocode(_ query: String) async throws -> [GeocodePlace] {
        var req = URLRequest(url: geocodeURL(base: baseURL, query: query))
        req.httpMethod = "GET"
        if let token = try tokens?.load() {
            req.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        let (data, response) = try await session.data(for: req)
        let status = (response as? HTTPURLResponse)?.statusCode ?? 0
        guard (200 ..< 300).contains(status) else { throw APIError.http(status) }
        let payload = try JSONSerialization.jsonObject(with: data) as? [String: Any] ?? [:]
        return geocodeResults(from: payload)
    }
}

@Observable
final class LocationSearchModel {
    var location = ""
    var latitude: Double?
    var longitude: Double?
    var results: [GeocodePlace] = []
    var client: EventsClient

    init(client: EventsClient) {
        self.client = client
    }

    func search(_ raw: String) async {
        let query = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        location = query
        guard query.count >= 3 else {
            results = []
            latitude = nil
            longitude = nil
            return
        }
        do {
            results = try await client.geocode(query)
        } catch {
            results = []
        }
    }

    func choose(_ place: GeocodePlace) {
        location = place.fullAddress
        latitude = place.latitude
        longitude = place.longitude
        results = []
    }
}

struct LocationSearchField: View {
    @Binding var location: String
    @Binding var latitude: Double?
    @Binding var longitude: Double?
    @State private var model: LocationSearchModel
    @State private var query: String

    init(location: Binding<String>, latitude: Binding<Double?>, longitude: Binding<Double?>, client: EventsClient) {
        _location = location
        _latitude = latitude
        _longitude = longitude
        _model = State(initialValue: LocationSearchModel(client: client))
        _query = State(initialValue: location.wrappedValue)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            PDATextField(
                GeocodeCopy.label,
                text: $query,
                capitalization: .never,
                disableAutocorrection: true
            )
            ForEach(model.results) { place in
                Button(place.fullAddress) {
                    model.choose(place)
                    location = model.location
                    latitude = model.latitude
                    longitude = model.longitude
                    query = model.location
                }
                .font(PDAType.control)
                .foregroundStyle(PDAColor.foreground)
            }
        }
        .onChange(of: query) { _, next in
            location = next
            Task { await model.search(next) }
        }
    }
}
