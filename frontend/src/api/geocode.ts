// Geocode search via the backend Photon proxy (/api/community/geocode/).
// Photon (komoot.io) is free, no API key. The backend adds NYC bias params
// and relays the response unchanged.

import { apiClient } from './client';

export interface PhotonResult {
  name: string;
  subtitle: string | null;
  fullAddress: string;
  lat: number;
  lon: number;
}

interface PhotonFeature {
  type: string;
  geometry: {
    type: string;
    coordinates: [number, number]; // [lon, lat] in GeoJSON
  };
  properties: {
    name?: string;
    housenumber?: string;
    street?: string;
    city?: string;
    state?: string;
    country?: string;
    postcode?: string;
    [key: string]: unknown;
  };
}

interface PhotonResponse {
  features: PhotonFeature[];
}

function abbreviateCity(city: string | null | undefined): string | null {
  if (!city) return null;
  if (city === 'New York') return 'ny';
  return city;
}

function parseFeature(f: PhotonFeature): PhotonResult {
  const props = f.properties;
  const coords = f.geometry.coordinates;
  const lon = coords[0];
  const lat = coords[1];

  const placeName = props.name ?? '';
  const streetAddress =
    props.housenumber && props.street
      ? `${props.housenumber} ${props.street}`
      : (props.street ?? null);

  const name = placeName.length > 0 ? placeName : (streetAddress ?? '');

  const subtitle = placeName && streetAddress ? streetAddress : (props.city ?? null);

  const cityLabel = abbreviateCity(props.city);

  const parts: string[] = [];
  if (placeName) parts.push(placeName);
  if (streetAddress && streetAddress !== placeName) parts.push(streetAddress);
  if (cityLabel && cityLabel !== placeName && cityLabel !== streetAddress) {
    parts.push(cityLabel);
  }

  return {
    name,
    subtitle,
    fullAddress: parts.join(', ').toLowerCase(),
    lat,
    lon,
  };
}

export async function searchLocations(query: string): Promise<PhotonResult[]> {
  if (query.trim().length < 3) return [];
  const { data } = await apiClient.get<PhotonResponse>('/api/community/geocode/', {
    params: { q: query.trim(), limit: 5 },
  });
  return data.features.map(parseFeature).filter((r) => r.name.length > 0);
}

// data.features is always present in Photon responses, but the ?? [] guard
// handles malformed responses gracefully.
