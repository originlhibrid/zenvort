/**
 * testAllRoutes.ts
 * ─────────────────────────────────────────────────────────────────────────────
 * End-to-end test of every supported conversion route.
 *
 * Sample files are loaded from SAMPLES_DIR (default: ./test-samples,
 * or C:\Users\palai\Documents\Projects\Zenvort\sample on Windows).
 *
 * Usage:
 *   pnpm --filter @zenvort/worker test-routes
 *   pnpm --filter @zenvort/worker test-routes -- --no-cleanup
 *   SAMPLES_DIR=C:\custom\path pnpm --filter @zenvort/worker test-routes
 *
 * Exit code:
 *   0  – all non-skipped routes passed
 *   1  – one or more routes failed
 * ─────────────────────────────────────────────────────────────────────────────
 */

import { existsSync, mkdirSync, readdirSync, unlinkSync, readFileSync, statSync, copyFileSync } from "fs";
import { resolve } from "path";
import sharp from "sharp";

// ── Direct imports from the worker ──────────────────────────────────────────
import { ROUTES } from "../routes.js";
import { executeConversion } from "../executor.js";
import { TMP_DIR } from "../security/pathGuard.js";

// Source directory: user-configurable, defaults to the external sample dir on
// Windows so files don't need to be inside TMP_DIR (which pathGuard guards).
const SAMPLES_SOURCE_DIR = resolve(
  process.env.SAMPLES_DIR ??
    (process.platform === "win32"
      ? "C:\\Users\\palai\\Documents\\Projects\\Zenvort\\sample"
      : "./test-samples")
);

// Staging directory — always inside TMP_DIR so pathGuard allows access.
// Sample files are copied here from SAMPLES_SOURCE_DIR before conversion.
const SAMPLES_DIR = resolve(TMP_DIR, "test-samples");
const RESULTS_DIR = resolve(TMP_DIR, "test-results");
const NO_CLEANUP = process.argv.includes("--no-cleanup");

// mkdir -p equivalent
try { mkdirSync(SAMPLES_DIR, { recursive: true }); } catch { /* exists */ }
try { mkdirSync(RESULTS_DIR, { recursive: true }); } catch { /* exists */ }

// ── ANSI colour codes ────────────────────────────────────────────────────────
const c = {
  red:    (s: string) => `\x1b[31m${s}\x1b[0m`,
  green:  (s: string) => `\x1b[32m${s}\x1b[0m`,
  yellow: (s: string) => `\x1b[33m${s}\x1b[0m`,
  cyan:   (s: string) => `\x1b[36m${s}\x1b[0m`,
  bold:   (s: string) => `\x1b[1m${s}\x1b[0m`,
};

// ── Sample discovery ─────────────────────────────────────────────────────────

const availableSamples = new Map<string, string>(); // format → absolute path

function scanSamples(): void {
  console.log(c.bold("\n🔍 Scanning for sample files…"));

  if (!existsSync(SAMPLES_SOURCE_DIR)) {
    printMissingSamples();
    process.exit(0);
  }

  let found = 0;
  for (const entry of readdirSync(SAMPLES_SOURCE_DIR)) {
    // Match "{format}.{format}" exactly, e.g. pdf.pdf, mp4.mp4
    const dot = entry.indexOf(".");
    if (dot === -1) continue;
    const stem = entry.slice(0, dot);
    const ext  = entry.slice(dot + 1);
    if (stem === ext) {
      const src  = resolve(SAMPLES_SOURCE_DIR, entry);
      const dest = resolve(SAMPLES_DIR, entry);
      try {
        copyFileSync(src, dest);
      } catch (err) {
        console.log(`  ${c.yellow("⚠")} ${stem}  — failed to copy: ${(err as Error).message}`);
        continue;
      }
      availableSamples.set(stem, dest);
      console.log(`  ${c.green("✓")} ${stem.padEnd(5)}  ${src}  →  ${dest}`);
      found++;
    }
  }

  if (found === 0) {
    printMissingSamples();
    process.exit(0);
  }

  // Warn about formats we know about but don't have files for
  const allFormats = [
    "pdf","docx","html","md",
    "jpg","png","mp4","mp3",
    "wav","xlsx","pptx",
  ];
  for (const fmt of allFormats) {
    if (!availableSamples.has(fmt)) {
      console.log(`  ${c.yellow("⚠")} ${fmt.padEnd(5)} — no sample file found`);
    }
  }

  console.log(`\n  ${found} sample(s) ready.\n`);
}

function printMissingSamples(): void {
  console.log(`
┌─────────────────────────────────────────────────────┐
│  No sample files found in ${SAMPLES_SOURCE_DIR.padEnd(29)} │
│                                                     │
│  Create the directory and add files named:          │
│    pdf.pdf   docx.docx   html.html   md.md          │
│    jpg.jpg   png.png     mp4.mp4     mp3.mp3        │
│    wav.wav   xlsx.xlsx   pptx.pptx                  │
│                                                     │
│  Then rerun:                                        │
│    pnpm --filter @zenvort/worker test-routes        │
│                                                     │
│  Or set a custom path:                              │
│    SAMPLES_DIR=C:\\your\\path pnpm ...test-routes    │
└─────────────────────────────────────────────────────┘
`);
}

// ── Output validation ────────────────────────────────────────────────────────

async function validateOutput(outputPath: string, outputFormat: string): Promise<string | null> {
  if (!existsSync(outputPath)) return "output file does not exist";
  const stat = await import("fs").then((fs) => fs.promises.stat(outputPath));
  if (stat.size === 0) return "output file is empty (0 bytes)";

  const header = readFileSync(outputPath);

  switch (outputFormat.toLowerCase()) {
    case "png":
    case "jpg":
    case "jpeg":
    case "webp":
    case "avif":
    case "gif":
    case "tiff":
    case "bmp": {
      const meta = await sharp(outputPath).metadata();
      if (!meta.width || !meta.height || meta.width === 0 || meta.height === 0) {
        return `invalid image dimensions: ${meta.width ?? "?"}×${meta.height ?? "?"}`;
      }
      break;
    }
    case "pdf": {
      if (!header.slice(0, 4).equals(Buffer.from("%PDF"))) {
        return "missing PDF magic bytes (%PDF)";
      }
      break;
    }
    case "txt":
    case "md": {
      const text = header.toString("utf-8").trim();
      if (!/[^\s]/.test(text)) return "txt file contains no non-whitespace characters";
      break;
    }
    case "docx":
    case "doc":
    case "odt":
    case "xlsx":
    case "ods":
    case "pptx":
    case "odp": {
      if (!header.slice(0, 2).equals(Buffer.from("PK"))) {
        return "missing ZIP magic bytes (PK) — not a valid Office XML file";
      }
      break;
    }
    default:
      break;
  }

  return null;
}

// ── Test runner ─────────────────────────────────────────────────────────────

type TestResult = {
  route: string;
  status: "PASS" | "FAIL" | "SKIP";
  converterUsed: string;
  durationMs: number;
  fallback: boolean;
  error: string;
};

function uuid(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (ch) => {
    const r = (Math.random() * 16) | 0;
    return (ch === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

async function runTests(): Promise<TestResult[]> {
  const results: TestResult[] = [];
  const routeKeys = Array.from(ROUTES.keys()).sort();

  console.log(c.bold("🚀 Running route tests…\n"));

  for (const routeKey of routeKeys) {
    const [inputFormat, outputFormat] = routeKey.split("→");
    const testId = uuid();

    // Check sample availability
    if (!availableSamples.has(inputFormat)) {
      results.push({ route: routeKey, status: "SKIP", converterUsed: "—", durationMs: 0, fallback: false, error: `no sample file for input format: ${inputFormat}` });
      continue;
    }

    const inputPath  = availableSamples.get(inputFormat)!;
    const outputPath = resolve(RESULTS_DIR, `${inputFormat}-to-${outputFormat}.${outputFormat}`);

    if (existsSync(outputPath)) {
      try { unlinkSync(outputPath); } catch { /* ignore */ }
    }

    const route = ROUTES.get(routeKey)!;
    const primaryConverter = route.converters[0]?.name ?? "?";

    let converterUsed = "—";
    let fallback = false;
    let durationMs = 0;
    let error = "";
    let status: TestResult["status"] = "SKIP";

    try {
      const start = Date.now();
      const { converterUsed: used } = await executeConversion(
        testId,
        inputPath,
        outputPath,
        inputFormat,
        outputFormat
      );
      durationMs = Date.now() - start;
      converterUsed = used;
      fallback = used !== primaryConverter;

      const validationError = await validateOutput(outputPath, outputFormat);
      if (validationError) {
        status = "FAIL";
        error = `output validation failed: ${validationError}`;
      } else {
        status = "PASS";
      }
    } catch (err) {
      status = "FAIL";
      error = err instanceof Error ? err.message : String(err);
    }

    results.push({ route: routeKey, status, converterUsed, durationMs, fallback, error });
  }

  return results;
}

// ── Results printer ─────────────────────────────────────────────────────────

function printResults(results: TestResult[]): void {
  const total     = results.length;
  const passed    = results.filter((r) => r.status === "PASS").length;
  const failed    = results.filter((r) => r.status === "FAIL").length;
  const skipped   = results.filter((r) => r.status === "SKIP").length;
  const fallbacks = results.filter((r) => r.fallback).length;

  console.log(c.bold("\nROUTE              STATUS   CONVERTER      DURATION  FALLBACK  ERROR"));
  console.log("─".repeat(82));

  for (const r of results) {
    const routeStr  = r.route.padEnd(19);
    const statusStr = (r.status === "PASS" ? c.green("PASS") : r.status === "FAIL" ? c.red("FAIL") : c.yellow("SKIP")).padEnd(7);
    const convStr   = r.converterUsed.padEnd(13);
    const durStr    = `${r.durationMs}ms`.padEnd(9);
    const fbStr     = r.fallback ? c.cyan("yes") : "no";
    const errStr    = r.error ? c.red(r.error) : "";

    console.log(`${routeStr} ${statusStr} ${convStr} ${durStr} ${fbStr.padEnd(9)} ${errStr}`);
  }

  console.log("─".repeat(82));

  const divider = "═".repeat(44);
  console.log(`\n${c.bold(divider)}`);
  console.log(`${c.bold("RESULTS")}   Total: ${total}   ${c.green("Passed:")} ${passed}   ${c.red("Failed:")} ${failed}   ${c.yellow("Skipped:")} ${skipped}`);
  if (fallbacks > 0) {
    console.log(`         ${c.cyan(`${fallbacks} route(s) used a fallback converter`)}`);
  }
  console.log(`${c.bold(divider)}\n`);
}

// ── Cleanup ─────────────────────────────────────────────────────────────────

function cleanup(): void {
  if (NO_CLEANUP) {
    console.log(c.yellow("ℹ  --no-cleanup set — results kept at ") + resolve(RESULTS_DIR) + "\n");
    return;
  }
  for (const file of readdirSync(RESULTS_DIR)) {
    try { unlinkSync(resolve(RESULTS_DIR, file)); } catch { /* locked file on Windows */ }
  }
  console.log(c.green("✓  Cleaned up test results.\n"));
}

// ── Main ─────────────────────────────────────────────────────────────────────

async function main() {
  console.log(c.bold("\n╔════════════════════════════════════════╗"));
  console.log(c.bold("║   ZENVORT — Route Test Suite          ║"));
  console.log(c.bold("╚════════════════════════════════════════╝\n"));

  scanSamples();
  const results = await runTests();
  printResults(results);
  cleanup();

  const hasFailures = results.some((r) => r.status === "FAIL");

  if (hasFailures) {
    console.error(c.red("✗  One or more routes failed."));
    process.exit(1);
  } else {
    console.log(c.green("✓  All routes passed."));
    process.exit(0);
  }
}

main().catch((err) => {
  console.error(c.red(`\nFatal: ${err instanceof Error ? err.message : err}`));
  process.exit(1);
});
