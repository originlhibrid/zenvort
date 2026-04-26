/**
 * pdftotext — PDF to plain text extractor.
 * Safe: spawn() with argument array. No shell interpolation.
 * Paths asserted inside /tmp/zenvort/.
 */

import { spawn } from "child_process";
import { existsSync } from "fs";
import { sanitizeAndAssertTmpPath } from "../security/pathGuard.js";

const CONVERTER_NAME = "pdftotext";
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

  await new Promise<void>((resolve, reject) => {
    const proc = spawn("pdftotext", [safeInput, safeOutput]);

    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      reject(new Error(`${CONVERTER_NAME}: Execution timed out after ${timeoutMs}ms`));
    }, timeoutMs);

    let stderr = "";
    proc.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) {
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
