/**
 * pdftoppm — PDF to image rasterizer.
 * Safe: spawn() with argument array. No shell interpolation.
 * Paths asserted inside /tmp/zenvort/.
 */

import { spawn } from "child_process";
import { existsSync } from "fs";
import { sanitizeAndAssertTmpPath } from "../security/pathGuard.js";

const CONVERTER_NAME = "pdftoppm";
const DEFAULT_TIMEOUT_MS = 60_000;

/** pdftoppm outputs a numbered file per page: input-1.png, input-2.png, etc.
 *  We read the first page and copy it to outputPath. */
const FIRST_PAGE = 1;

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

  // Build a base name for pdftoppm output — it appends -N.{ext}
  const baseName = `page-${FIRST_PAGE}`;
  const tmpBase = `/tmp/zenvort/${baseName}`;

  await new Promise<void>((resolve, reject) => {
    const proc = spawn("pdftoppm", [
      "-r", "150",
      "-f", String(FIRST_PAGE),
      "-l", String(FIRST_PAGE),
      // Format flag: -png, -jpeg, or -jpg
      outputFormat === "jpg" || outputFormat === "jpeg" ? "-jpeg" : "-png",
      safeInput,
      tmpBase,
    ]);

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

  // pdftoppm named the file page-1.{ext} — copy it to the expected outputPath
  const generatedPageFile = `${tmpBase}-${FIRST_PAGE}.${outputFormat === "jpg" || outputFormat === "jpeg" ? "jpg" : "png"}`;

  if (existsSync(generatedPageFile)) {
    await import("fs").then(async (fs) => {
      await fs.promises.copyFile(generatedPageFile, safeOutput);
      await fs.promises.unlink(generatedPageFile).catch(() => {});
    });
  } else {
    throw new Error(`${CONVERTER_NAME}: Expected page file not found: ${generatedPageFile}`);
  }

  const duration = Date.now() - startTime;
  console.log(`${CONVERTER_NAME} converted ${inputFormat} → ${outputFormat} in ${duration}ms`);
}
