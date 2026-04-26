/**
 * MIME type validation before R2 upload.
 *
 * Uses `file-type` to detect the actual MIME type of the output file.
 * Asserts it matches the expected output format — prevents a converter
 * silently outputting the wrong file type.
 */

import { fileTypeFromBuffer } from "file-type";
import { readFile } from "fs/promises";
import { stat } from "fs/promises";

export const MIME_BY_FORMAT: Record<string, string[]> = {
  // Images
  png: ["image/png"],
  jpg: ["image/jpeg"],
  jpeg: ["image/jpeg"],
  webp: ["image/webp"],
  avif: ["image/avif"],
  gif: ["image/gif"],
  tiff: ["image/tiff", "image/tiff"],
  bmp: ["image/bmp"],
  svg: ["image/svg+xml"],

  // Documents
  pdf: ["application/pdf"],
  docx: [
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  ],
  doc: ["application/msword"],
  html: ["text/html"],
  txt: ["text/plain"],
  md: ["text/markdown"],

  // Spreadsheets
  xlsx: [
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  ],
  csv: ["text/csv"],
  ods: ["application/vnd.oasis.opendocument.spreadsheet"],

  // Presentations
  pptx: [
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
  ],
  odp: ["application/vnd.oasis.opendocument.presentation"],

  // Audio
  mp3: ["audio/mpeg"],
  wav: ["audio/wav", "audio/x-wav"],
  aac: ["audio/aac"],
  flac: ["audio/flac"],
  ogg: ["audio/ogg"],
  m4a: ["audio/mp4"],
  opus: ["audio/opus"],
  wma: ["audio/x-ms-wma"],

  // Video
  mp4: ["video/mp4"],
  webm: ["video/webm"],
  mov: ["video/quicktime"],
  avi: ["video/x-msvideo"],
  mkv: ["video/x-matroska"],
  flv: ["video/x-flv"],
  wmv: ["video/x-ms-wmv"],
  m4v: ["video/x-m4v"],
  gif_img: ["image/gif"], // FFmpeg GIF output
};

/**
 * Detect the MIME type of a file on disk using file-type.
 * Returns null if detection fails.
 */
export async function detectMimeType(filePath: string): Promise<string | null> {
  const buffer = await readFile(filePath);
  const result = await fileTypeFromBuffer(buffer);
  return result?.mime ?? null;
}

/**
 * Assert that the output file's detected MIME type matches the expected
 * outputFormat. Throws if they don't match.
 *
 * FFmpeg GIF outputs are detected as image/gif rather than video/gif —
 * we treat "gif_img" variant for that case.
 */
export async function assertMimeTypeMatches(
  filePath: string,
  outputFormat: string,
  jobId: string
): Promise<void> {
  const detectedMime = await detectMimeType(filePath);

  // Special-case FFmpeg GIF: detected as image/gif but format key is "gif"
  const lookupKey = outputFormat === "gif" ? "gif_img" : outputFormat;
  const expectedMimes = MIME_BY_FORMAT[lookupKey];

  if (!expectedMimes) {
    // Unknown format — warn but don't block the upload
    console.warn(
      `[${jobId}] No MIME allowlist for format "${outputFormat}" — skipping MIME validation`
    );
    return;
  }

  if (!detectedMime) {
    throw new Error(
      `MIME detection failed for "${filePath}" — file may be corrupted or unsupported`
    );
  }

  if (!expectedMimes.includes(detectedMime)) {
    throw new Error(
      `MIME mismatch: expected one of [${expectedMimes.join(", ")}], got "${detectedMime}" for format "${outputFormat}"`
    );
  }
}
