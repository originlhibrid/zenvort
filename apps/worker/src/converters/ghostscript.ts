/**
 * Ghostscript — PDF/PostScript processor.
 * Safe: spawn() with argument array. No shell interpolation.
 * Paths asserted inside /tmp/zenvort/.
 *
 * Uses gs -sDEVICE=png16m for raster output or -sDEVICE=pdfwrite for PDF.
 */

import { spawn } from "child_process";
import { existsSync } from "fs";
import { sanitizeAndAssertTmpPath } from "../security/pathGuard.js";

const CONVERTER_NAME = "ghostscript";
const DEFAULT_TIMEOUT_MS = 120_000;

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

  // Choose device based on output format
  const device =
    outputFormat === "pdf" || outputFormat === "pdf"
      ? "pdfwrite"
      : "png16m";

  const args = [
    `-sDEVICE=${device}`,
    "-dNOPAUSE",
    "-dBATCH",
    "-dSAFER",
    `-sOutputFile=${safeOutput}`,
    safeInput,
  ];

  await new Promise<void>((resolve, reject) => {
    const proc = spawn("gs", args);

    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      reject(new Error(`${CONVERTER_NAME}: Execution timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    let stderr = "";
    proc.on("close", (code) => {
      clearTimeout(timer);
      // Ghostscript sometimes exits with code 0 or null on success
      if (code === 0 || code === null) {
        resolve();
      } else {
        reject(new Error(`${CONVERTER_NAME}: Process exited with code ${code}. stderr=${stderr}`));
      }
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(new Error(`${CONVERTER_NAME}: Failed to spawn. stderr=${stderr} error=${err.message}`));
    });
  }).catch(async (err) => {
    if (existsSync(safeOutput)) {
      await import("fs").then((fs) => fs.promises.unlink(safeOutput).catch(() => {}));
    }
    throw err;
  });

  const duration = Date.now() - startTime;
  console.log(`${CONVERTER_NAME} converted ${inputFormat} → ${outputFormat} in ${duration}ms`);
}
