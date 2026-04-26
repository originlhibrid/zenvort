/**
 * Sharp — high-performance Node.js image processor.
 * Safe: pure Node.js API, no shell calls.
 * Paths asserted inside /tmp/zenvort/ before any I/O.
 */

import sharp from "sharp";
import { existsSync } from "fs";
import { sanitizeAndAssertTmpPath } from "../security/pathGuard.js";

const CONVERTER_NAME = "sharp";
const DEFAULT_TIMEOUT_MS = 30_000;

export async function convert(
  inputPath: string,
  outputPath: string,
  inputFormat: string,
  outputFormat: string,
  timeoutMs: number = DEFAULT_TIMEOUT_MS
): Promise<void> {
  const safeInput = sanitizeAndAssertTmpPath(inputPath);
  const safeOutput = sanitizeAndAssertTmpPath(outputPath);

  if (!existsSync(safeInput)) {
    throw new Error(`${CONVERTER_NAME}: Input file does not exist: ${safeInput}`);
  }

  const startTime = Date.now();

  let pipeline = sharp(safeInput);

  switch (outputFormat.toLowerCase()) {
    case "jpg":
    case "jpeg":
      pipeline = pipeline.jpeg({ quality: 90 });
      break;
    case "png":
      pipeline = pipeline.png({ compressionLevel: 9 });
      break;
    case "webp":
      pipeline = pipeline.webp({ quality: 90 });
      break;
    case "avif":
      pipeline = pipeline.avif({ quality: 80 });
      break;
    case "tiff":
      pipeline = pipeline.tiff({ compression: "lzw" });
      break;
    case "gif":
      pipeline = pipeline.gif();
      break;
    default: {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      pipeline = pipeline.toFormat(outputFormat as any);
    }
  }

  const timer = setTimeout(() => {
    throw new Error(`${CONVERTER_NAME}: Execution timed out after ${timeoutMs}ms`);
  }, timeoutMs);

  try {
    await pipeline.toFile(safeOutput);
  } catch (err) {
    clearTimeout(timer);
    if (existsSync(safeOutput)) {
      await import("fs").then((fs) => fs.promises.unlink(safeOutput).catch(() => {}));
    }
    const message = err instanceof Error ? err.message : String(err);
    throw new Error(`${CONVERTER_NAME}: ${message}`);
  }

  clearTimeout(timer);

  const duration = Date.now() - startTime;
  console.log(`${CONVERTER_NAME} converted ${inputFormat} → ${outputFormat} in ${duration}ms`);
}
