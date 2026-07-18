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

// iOS Safari can leave Image.onload / canvas.toBlob callbacks pending forever; bound them (issue 580).
const IMAGE_OP_TIMEOUT_MS = 15000;

function withTimeout<T>(promise: Promise<T>, message: string): Promise<T> {
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => {
      reject(new Error(message));
    }, IMAGE_OP_TIMEOUT_MS);
    promise.then(resolve, reject).finally(() => {
      clearTimeout(timer);
    });
  });
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return withTimeout(
    new Promise<HTMLImageElement>((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        resolve(img);
      };
      img.onerror = () => {
        reject(new Error('failed to load image'));
      };
      img.src = src;
    }),
    'timed out loading image',
  );
}

function canvasToBlob(canvas: HTMLCanvasElement): Promise<Blob> {
  return withTimeout(
    new Promise<Blob>((resolve, reject) => {
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error('canvas.toBlob returned null'));
      }, 'image/png');
    }),
    'timed out processing image',
  );
}
