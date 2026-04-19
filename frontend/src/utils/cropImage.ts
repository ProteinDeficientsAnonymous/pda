// Canvas-based image crop. Given a source image blob and a crop rect (in
// source pixels), produces a cropped PNG Blob. react-easy-crop gives us the
// rect; we do the actual compositing. Output dimensions preserve the crop
// area's aspect ratio, bounded by maxSize on the longer edge.

export interface CropArea {
  x: number;
  y: number;
  width: number;
  height: number;
}

export async function cropImage(source: Blob, area: CropArea, maxSize = 512): Promise<Blob> {
  const url = URL.createObjectURL(source);
  try {
    const img = await loadImage(url);
    const canvas = document.createElement('canvas');
    const { width, height } = fitToMaxSize(area.width, area.height, maxSize);
    canvas.width = width;
    canvas.height = height;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('canvas 2d context unavailable');
    ctx.drawImage(img, area.x, area.y, area.width, area.height, 0, 0, width, height);
    return await canvasToBlob(canvas);
  } finally {
    URL.revokeObjectURL(url);
  }
}

function fitToMaxSize(w: number, h: number, maxSize: number): { width: number; height: number } {
  const longer = Math.max(w, h);
  if (longer <= maxSize) return { width: Math.round(w), height: Math.round(h) };
  const scale = maxSize / longer;
  return { width: Math.round(w * scale), height: Math.round(h * scale) };
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.onload = () => {
      resolve(img);
    };
    img.onerror = () => {
      reject(new Error('failed to load image'));
    };
    img.src = src;
  });
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => {
      if (blob) resolve(blob);
      else reject(new Error('canvas.toBlob returned null'));
    }, 'image/png');
  });
}
