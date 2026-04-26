/**
 * Conversion routing table.
 * Key: "inputFormat→outputFormat" (e.g. "pdf→png")
 * Value: ordered list of converters to try as fallbacks.
 *
 * Adding a new route key to packages/shared/src/routes.ts ROUTE_KEYS
 * automatically enables it in the API. This file adds the actual
 * converter implementations.
 */

import { ROUTE_KEYS } from "@zenvort/shared";
import type { ConversionRoute } from "@zenvort/shared";

import { convert as libreofficeConvert } from "./converters/libreoffice.js";
import { convert as ffmpegConvert } from "./converters/ffmpeg.js";
import { convert as pdftoppmConvert } from "./converters/pdftoppm.js";
import { convert as pdftotextConvert } from "./converters/pdftotext.js";
import { convert as pandocConvert } from "./converters/pandoc.js";
import { convert as sharpConvert } from "./converters/sharp.js";
import { convert as imagemagickConvert } from "./converters/imagemagick.js";
import { convert as ghostscriptConvert } from "./converters/ghostscript.js";

// Route definitions: converter name → actual function
const CONVERTERS = {
  libreoffice: libreofficeConvert,
  ffmpeg: ffmpegConvert,
  pdftoppm: pdftoppmConvert,
  pdftotext: pdftotextConvert,
  pandoc: pandocConvert,
  sharp: sharpConvert,
  imagemagick: imagemagickConvert,
  ghostscript: ghostscriptConvert,
} as const;

// Maps a readable route key (e.g. "pdf→png") → converter identifier names
// (kept as strings so the converter name string is preserved for metrics/logging)
const ROUTE_DEFINITIONS: Record<string, string[]> = {
  // ── Image → Image ───────────────────────────────────────────────────────────
  "jpg→png": ["sharp", "imagemagick"],
  "jpg→webp": ["sharp", "imagemagick"],
  "jpg→avif": ["sharp"],

  "jpeg→png": ["sharp", "imagemagick"],
  "jpeg→webp": ["sharp", "imagemagick"],
  "jpeg→avif": ["sharp"],

  "png→jpg": ["sharp", "imagemagick"],
  "png→webp": ["sharp", "imagemagick"],
  "png→avif": ["sharp"],
  "png→pdf": ["imagemagick", "ghostscript"],

  "webp→png": ["sharp", "imagemagick"],
  "webp→jpg": ["sharp", "imagemagick"],
  "webp→avif": ["sharp"],

  "gif→png": ["sharp", "imagemagick"],
  "gif→jpg": ["sharp", "imagemagick"],
  "gif→webp": ["sharp", "imagemagick"],

  "tiff→png": ["sharp", "imagemagick"],
  "tiff→jpg": ["sharp", "imagemagick"],
  "tiff→webp": ["sharp", "imagemagick"],
  "tiff→pdf": ["imagemagick", "ghostscript"],

  "bmp→png": ["sharp", "imagemagick"],
  "bmp→jpg": ["sharp", "imagemagick"],
  "bmp→webp": ["sharp", "imagemagick"],

  // ── PDF ─────────────────────────────────────────────────────────────────────
  "pdf→png": ["pdftoppm", "imagemagick"],
  "pdf→jpg": ["pdftoppm", "imagemagick"],
  "pdf→txt": ["pdftotext", "libreoffice"],
  "pdf→docx": ["libreoffice"],
  "pdf→html": ["libreoffice"],
  "pdf→pdf": ["ghostscript"],

  // ── Documents ───────────────────────────────────────────────────────────────
  "docx→pdf": ["libreoffice", "pandoc"],
  "docx→txt": ["libreoffice", "pandoc"],
  "docx→html": ["libreoffice", "pandoc"],
  "docx→doc": ["libreoffice"],

  "doc→pdf": ["libreoffice", "pandoc"],
  "doc→txt": ["libreoffice", "pandoc"],
  "doc→html": ["libreoffice", "pandoc"],
  "doc→docx": ["libreoffice"],

  "odt→pdf": ["libreoffice", "pandoc"],
  "odt→txt": ["libreoffice", "pandoc"],
  "odt→html": ["libreoffice", "pandoc"],
  "odt→docx": ["libreoffice"],

  // ── Markdown ────────────────────────────────────────────────────────────────
  "md→pdf": ["pandoc", "libreoffice"],
  "md→docx": ["pandoc"],
  "md→html": ["libreoffice", "pandoc"],
  "md→txt": ["libreoffice", "pandoc"],

  // ── HTML ────────────────────────────────────────────────────────────────────
  "html→pdf": ["libreoffice", "pandoc"],
  "html→docx": ["libreoffice", "pandoc"],
  "html→txt": ["libreoffice", "pandoc"],
  "html→md": ["pandoc"],

  // ── Spreadsheets ─────────────────────────────────────────────────────────────
  "xlsx→csv": ["libreoffice"],
  "xlsx→pdf": ["libreoffice"],
  "xlsx→ods": ["libreoffice"],

  "csv→xlsx": ["libreoffice"],
  "csv→ods": ["libreoffice"],
  "csv→pdf": ["libreoffice"],

  "ods→csv": ["libreoffice"],
  "ods→xlsx": ["libreoffice"],
  "ods→pdf": ["libreoffice"],

  // ── Presentations ────────────────────────────────────────────────────────────
  "pptx→pdf": ["libreoffice"],
  "pptx→odp": ["libreoffice"],

  "odp→pdf": ["libreoffice"],
  "odp→pptx": ["libreoffice"],

  // ── Audio ─────────────────────────────────────────────────────────────────────
  "mp3→wav": ["ffmpeg"],
  "wav→mp3": ["ffmpeg"],
  "wav→aac": ["ffmpeg"],
  "wav→flac": ["ffmpeg"],
  "wav→ogg": ["ffmpeg"],
  "mp3→aac": ["ffmpeg"],
  "mp3→flac": ["ffmpeg"],
  "mp3→ogg": ["ffmpeg"],
  "aac→mp3": ["ffmpeg"],
  "aac→wav": ["ffmpeg"],
  "flac→mp3": ["ffmpeg"],
  "flac→wav": ["ffmpeg"],
  "ogg→mp3": ["ffmpeg"],
  "ogg→wav": ["ffmpeg"],
  "m4a→mp3": ["ffmpeg"],
  "m4a→wav": ["ffmpeg"],
  "opus→mp3": ["ffmpeg"],
  "opus→wav": ["ffmpeg"],
  "wma→mp3": ["ffmpeg"],
  "wma→wav": ["ffmpeg"],

  // ── Video ───────────────────────────────────────────────────────────────────
  "mp4→webm": ["ffmpeg"],
  "mp4→mkv": ["ffmpeg"],
  "mp4→mov": ["ffmpeg"],
  "mp4→avi": ["ffmpeg"],
  "mp4→mp3": ["ffmpeg"],
  "mp4→gif": ["ffmpeg"],
  "mp4→mp4": ["ffmpeg"],

  "webm→mp4": ["ffmpeg"],
  "mov→mp4": ["ffmpeg"],
  "mov→webm": ["ffmpeg"],
  "avi→mp4": ["ffmpeg"],
  "mkv→mp4": ["ffmpeg"],
  "flv→mp4": ["ffmpeg"],
  "wmv→mp4": ["ffmpeg"],
  "mts→mp4": ["ffmpeg"],
  "ts→mp4": ["ffmpeg"],
};

// Descriptions for each route
const ROUTE_DESCRIPTIONS: Record<string, string> = {
  // ── Image → Image
  "jpg→png": "JPEG to PNG",
  "jpg→webp": "JPEG to WebP",
  "jpg→avif": "JPEG to AVIF",
  "jpeg→png": "JPEG to PNG",
  "jpeg→webp": "JPEG to WebP",
  "jpeg→avif": "JPEG to AVIF",
  "png→jpg": "PNG to JPEG",
  "png→webp": "PNG to WebP",
  "png→avif": "PNG to AVIF",
  "png→pdf": "PNG to PDF",
  "webp→png": "WebP to PNG",
  "webp→jpg": "WebP to JPEG",
  "webp→avif": "WebP to AVIF",
  "gif→png": "GIF to PNG",
  "gif→jpg": "GIF to JPEG",
  "gif→webp": "GIF to WebP",
  "tiff→png": "TIFF to PNG",
  "tiff→jpg": "TIFF to JPEG",
  "tiff→webp": "TIFF to WebP",
  "tiff→pdf": "TIFF to PDF",
  "bmp→png": "BMP to PNG",
  "bmp→jpg": "BMP to JPEG",
  "bmp→webp": "BMP to WebP",

  // PDF
  "pdf→png": "PDF to PNG",
  "pdf→jpg": "PDF to JPEG",
  "pdf→txt": "PDF to text",
  "pdf→docx": "PDF to DOCX",
  "pdf→html": "PDF to HTML",
  "pdf→pdf": "PDF compression",

  // Documents
  "docx→pdf": "DOCX to PDF",
  "docx→txt": "DOCX to text",
  "docx→html": "DOCX to HTML",
  "docx→doc": "DOCX to DOC",
  "doc→pdf": "DOC to PDF",
  "doc→txt": "DOC to text",
  "doc→html": "DOC to HTML",
  "doc→docx": "DOC to DOCX",
  "odt→pdf": "ODT to PDF",
  "odt→txt": "ODT to text",
  "odt→html": "ODT to HTML",
  "odt→docx": "ODT to DOCX",

  // Markdown
  "md→pdf": "Markdown to PDF",
  "md→docx": "Markdown to DOCX",
  "md→html": "Markdown to HTML",
  "md→txt": "Markdown to text",

  // HTML
  "html→pdf": "HTML to PDF",
  "html→docx": "HTML to DOCX",
  "html→txt": "HTML to text",
  "html→md": "HTML to Markdown",

  // Spreadsheets
  "xlsx→csv": "Excel to CSV",
  "xlsx→pdf": "Excel to PDF",
  "xlsx→ods": "Excel to ODS",
  "csv→xlsx": "CSV to Excel",
  "csv→ods": "CSV to ODS",
  "csv→pdf": "CSV to PDF",
  "ods→csv": "ODS to CSV",
  "ods→xlsx": "ODS to Excel",
  "ods→pdf": "ODS to PDF",

  // Presentations
  "pptx→pdf": "PowerPoint to PDF",
  "pptx→odp": "PowerPoint to ODP",
  "odp→pdf": "ODP to PDF",
  "odp→pptx": "ODP to PowerPoint",

  // Audio
  "mp3→wav": "MP3 to WAV",
  "wav→mp3": "WAV to MP3",
  "wav→aac": "WAV to AAC",
  "wav→flac": "WAV to FLAC",
  "wav→ogg": "WAV to OGG",
  "mp3→aac": "MP3 to AAC",
  "mp3→flac": "MP3 to FLAC",
  "mp3→ogg": "MP3 to OGG",
  "aac→mp3": "AAC to MP3",
  "aac→wav": "AAC to WAV",
  "flac→mp3": "FLAC to MP3",
  "flac→wav": "FLAC to WAV",
  "ogg→mp3": "OGG to MP3",
  "ogg→wav": "OGG to WAV",
  "m4a→mp3": "M4A to MP3",
  "m4a→wav": "M4A to WAV",
  "opus→mp3": "Opus to MP3",
  "opus→wav": "Opus to WAV",
  "wma→mp3": "WMA to MP3",
  "wma→wav": "WMA to WAV",

  // Video
  "mp4→webm": "MP4 to WebM",
  "mp4→mkv": "MP4 to MKV",
  "mp4→mov": "MP4 to MOV",
  "mp4→avi": "MP4 to AVI",
  "mp4→mp3": "MP4 to MP3 (extract audio)",
  "mp4→gif": "MP4 to GIF",
  "mp4→mp4": "MP4 recompress",
  "webm→mp4": "WebM to MP4",
  "mov→mp4": "MOV to MP4",
  "mov→webm": "MOV to WebM",
  "avi→mp4": "AVI to MP4",
  "mkv→mp4": "MKV to MP4",
  "flv→mp4": "FLV to MP4",
  "wmv→mp4": "WMV to MP4",
  "mts→mp4": "MTS to MP4",
  "ts→mp4": "TS to MP4",
};

export type { ConversionRoute } from "@zenvort/shared";

// Build the ROUTES Map from the definitions
export const ROUTES: Map<string, ConversionRoute> = new Map(
  ROUTE_KEYS.map((key) => {
    const converterNames = ROUTE_DEFINITIONS[key] ?? [];
    const converters = converterNames.map((name) => {
      const fn = CONVERTERS[name as keyof typeof CONVERTERS];
      if (!fn) throw new Error(`No converter registered for name: ${name}`);
      return fn;
    });
    return [key, { converters, description: ROUTE_DESCRIPTIONS[key] ?? key }];
  })
);

/**
 * Looks up a route by input→output format pair.
 * Returns null if no route is defined.
 */
export function getRoute(
  inputFormat: string,
  outputFormat: string
): ConversionRoute | null {
  return ROUTES.get(`${inputFormat.toLowerCase()}→${outputFormat.toLowerCase()}`) ?? null;
}
