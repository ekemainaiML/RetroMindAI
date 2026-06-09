export function detectBlur(imageData: ImageData): { isBlurry: boolean; variance: number } {
  const data = imageData.data;
  const w = imageData.width;
  const h = imageData.height;

  let sum = 0;
  let sumSq = 0;
  let count = 0;

  for (let y = 1; y < h - 1; y++) {
    for (let x = 1; x < w - 1; x++) {
      const idx = (y * w + x) * 4;
      const gray = 0.299 * data[idx] + 0.587 * data[idx + 1] + 0.114 * data[idx + 2];

      const top = 0.299 * data[((y - 1) * w + x) * 4]
        + 0.587 * data[((y - 1) * w + x) * 4 + 1]
        + 0.114 * data[((y - 1) * w + x) * 4 + 2];
      const bottom = 0.299 * data[((y + 1) * w + x) * 4]
        + 0.587 * data[((y + 1) * w + x) * 4 + 1]
        + 0.114 * data[((y + 1) * w + x) * 4 + 2];
      const left = 0.299 * data[(y * w + (x - 1)) * 4]
        + 0.587 * data[(y * w + (x - 1)) * 4 + 1]
        + 0.114 * data[(y * w + (x - 1)) * 4 + 2];
      const right = 0.299 * data[(y * w + (x + 1)) * 4]
        + 0.587 * data[(y * w + (x + 1)) * 4 + 1]
        + 0.114 * data[(y * w + (x + 1)) * 4 + 2];

      const laplacian = Math.abs(4 * gray - top - bottom - left - right);
      sum += laplacian;
      sumSq += laplacian * laplacian;
      count++;
    }
  }

  const variance = count > 0 ? sumSq / count - (sum / count) * (sum / count) : 0;
  return { isBlurry: variance < 120, variance };
}

export function captureFrame(video: HTMLVideoElement): Promise<Blob | null> {
  const canvas = document.createElement("canvas");
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const ctx = canvas.getContext("2d");
  if (!ctx) return Promise.resolve(null);
  ctx.drawImage(video, 0, 0);
  return new Promise<Blob | null>((resolve) => {
    canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.85);
  });
}
