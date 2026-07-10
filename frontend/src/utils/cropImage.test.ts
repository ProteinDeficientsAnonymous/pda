import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { cropImage } from './cropImage';

const AREA = { x: 0, y: 0, width: 100, height: 100 };

function stubImageThatLoads() {
  class FakeImage {
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    set src(_v: string) {
      queueMicrotask(() => this.onload?.());
    }
  }
  vi.stubGlobal('Image', FakeImage);
}

beforeEach(() => {
  vi.stubGlobal('URL', {
    createObjectURL: vi.fn().mockReturnValue('blob:mock'),
    revokeObjectURL: vi.fn(),
  });
  vi.spyOn(HTMLCanvasElement.prototype, 'getContext').mockReturnValue({
    drawImage: vi.fn(),
  } as unknown as CanvasRenderingContext2D);
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
  vi.useRealTimers();
});

describe('cropImage', () => {
  it('rejects instead of hanging when canvas.toBlob never calls back (issue 580)', async () => {
    vi.useFakeTimers();
    stubImageThatLoads();
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation(() => {
      // never invokes the callback — mimics iOS Safari wedging
    });

    const promise = cropImage(new Blob(['x']), AREA);
    const assertion = expect(promise).rejects.toThrow(/timed out processing image/i);
    await vi.advanceTimersByTimeAsync(15000);
    await assertion;
  });

  it('resolves with the blob when toBlob succeeds', async () => {
    stubImageThatLoads();
    const out = new Blob(['png'], { type: 'image/png' });
    vi.spyOn(HTMLCanvasElement.prototype, 'toBlob').mockImplementation((cb) => {
      cb(out);
    });

    await expect(cropImage(new Blob(['x']), AREA)).resolves.toBe(out);
  });
});
