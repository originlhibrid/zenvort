// Shared types for the conversion routing system.
// These types are used by both the API (for validation) and the worker (for execution).
// The actual ROUTES map with converter implementations lives in apps/worker/src/routes.ts.

export type ConverterFn = (
  inputPath: string,
  outputPath: string,
  inputFormat: string,
  outputFormat: string,
  timeoutMs?: number
) => Promise<void>;

export type RouteKey = string; // e.g. "pdf→png"
export type ConversionRoute = {
  converters: ConverterFn[];
  description: string;
};

/**
 * Static route keys used to populate VALID_INPUT_FORMATS and VALID_OUTPUT_FORMATS
 * in the API. Adding a new key here automatically enables it everywhere.
 * The worker uses these keys to build the full ROUTES map with actual converter functions.
 */
export const ROUTE_KEYS: RouteKey[] = [
  // ── Image → Image ───────────────────────────────────────────────────────────
  "jpg→png", "jpg→webp", "jpg→avif",
  "jpeg→png", "jpeg→webp", "jpeg→avif",
  "png→jpg", "png→webp", "png→avif", "png→pdf",
  "webp→png", "webp→jpg", "webp→avif",
  "gif→png", "gif→jpg", "gif→webp",
  "tiff→png", "tiff→jpg", "tiff→webp", "tiff→pdf",
  "bmp→png", "bmp→jpg", "bmp→webp",

  // ── PDF ─────────────────────────────────────────────────────────────────────
  "pdf→png", "pdf→jpg", "pdf→txt", "pdf→docx", "pdf→html", "pdf→pdf",

  // ── Documents ───────────────────────────────────────────────────────────────
  "docx→pdf", "docx→txt", "docx→html", "docx→doc",
  "doc→pdf", "doc→txt", "doc→html", "doc→docx",
  "odt→pdf", "odt→txt", "odt→html", "odt→docx",

  // ── Markdown ────────────────────────────────────────────────────────────────
  "md→pdf", "md→docx", "md→html", "md→txt",

  // ── HTML ────────────────────────────────────────────────────────────────────
  "html→pdf", "html→docx", "html→txt", "html→md",

  // ── Spreadsheets ─────────────────────────────────────────────────────────────
  "xlsx→csv", "xlsx→pdf", "xlsx→ods",
  "csv→xlsx", "csv→ods", "csv→pdf",
  "ods→csv", "ods→xlsx", "ods→pdf",

  // ── Presentations ────────────────────────────────────────────────────────────
  "pptx→pdf", "pptx→odp",
  "odp→pdf", "odp→pptx",

  // ── Audio ─────────────────────────────────────────────────────────────────────
  "mp3→wav", "wav→mp3", "wav→aac", "wav→flac", "wav→ogg",
  "mp3→aac", "mp3→flac", "mp3→ogg",
  "aac→mp3", "aac→wav",
  "flac→mp3", "flac→wav",
  "ogg→mp3", "ogg→wav",
  "m4a→mp3", "m4a→wav",
  "opus→mp3", "opus→wav",
  "wma→mp3", "wma→wav",

  // ── Video ───────────────────────────────────────────────────────────────────
  "mp4→webm", "mp4→mkv", "mp4→mov", "mp4→avi", "mp4→mp3", "mp4→gif", "mp4→mp4",
  "webm→mp4", "mov→mp4", "mov→webm",
  "avi→mp4", "mkv→mp4", "flv→mp4", "wmv→mp4",
  "mts→mp4", "ts→mp4",
];

/**
 * Derives input formats, output formats, and all supported conversion pairs
 * dynamically from ROUTE_KEYS. Adding a new key to ROUTE_KEYS automatically
 * updates all three lists — no other code changes needed.
 */
export function getSupportedFormats(): {
  inputFormats: string[];
  outputFormats: string[];
  pairs: string[];
} {
  const inputFormats = new Set<string>();
  const outputFormats = new Set<string>();
  const pairs: string[] = [];

  for (const key of ROUTE_KEYS) {
    const [input, output] = key.split("→");
    inputFormats.add(input);
    outputFormats.add(output);
    pairs.push(key);
  }

  return {
    inputFormats: Array.from(inputFormats).sort(),
    outputFormats: Array.from(outputFormats).sort(),
    pairs: [...pairs].sort(),
  };
}

/**
 * Looks up a route by input→output format pair.
 * Returns null if no route exists.
 *
 * The full ROUTES Map with converter implementations lives in
 * apps/worker/src/routes.ts. This function is re-exported from there
 * so callers can use the same interface regardless of package.
 */
export function getRoute(
  routes: Map<string, { converters: ConverterFn[]; description: string }>,
  inputFormat: string,
  outputFormat: string
): { converters: ConverterFn[]; description: string } | null {
  return routes.get(`${inputFormat.toLowerCase()}→${outputFormat.toLowerCase()}`) ?? null;
}
