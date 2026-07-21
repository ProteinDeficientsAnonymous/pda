export interface LibraryImage {
  id: string;
  label: string;
  dataUrl: string;
}

function swatch(bg: string, emoji: string): string {
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="600" height="750" viewBox="0 0 600 750"><rect width="600" height="750" fill="${bg}"/><text x="300" y="405" font-size="220" text-anchor="middle" dominant-baseline="middle">${emoji}</text></svg>`;
  return `data:image/svg+xml;utf8,${encodeURIComponent(svg)}`;
}

export const EVENT_LIBRARY_IMAGES: LibraryImage[] = [
  { id: 'sprout', label: 'sprout', dataUrl: swatch('#CCE8E4', '🌱') },
  { id: 'carrot', label: 'carrot', dataUrl: swatch('#FFE0B2', '🥕') },
  { id: 'avocado', label: 'avocado', dataUrl: swatch('#D0E8FF', '🥑') },
  { id: 'mushroom', label: 'mushroom', dataUrl: swatch('#E0D0F0', '🍄') },
  { id: 'sunflower', label: 'sunflower', dataUrl: swatch('#FFE0B2', '🌻') },
  { id: 'grapes', label: 'grapes', dataUrl: swatch('#E0D0F0', '🍇') },
  { id: 'leafy', label: 'leafy greens', dataUrl: swatch('#CCE8E4', '🥬') },
  { id: 'campfire', label: 'campfire', dataUrl: swatch('#D0E8FF', '🔥') },
  { id: 'plate', label: 'plate', dataUrl: swatch('#FFE0B2', '🍽️') },
  { id: 'balloon', label: 'balloon', dataUrl: swatch('#D0E8FF', '🎈') },
];
