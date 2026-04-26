/**
 * LibreOffice headless converter.
 *
 * Safety:
 *   - spawn() with argument array — no shell interpolation.
 *   - Paths asserted inside /tmp/zenvort/ before any system call.
 *
 * Concurrency:
 *   - Per-process mutex serializes all LibreOffice conversions so they
 *     never overlap even when BullMQ concurrency > 1.
 *   - Each job gets an isolated --user-installation profile so parallel
 *     instances (across different processes) don't conflict either.
 */

import { spawn } from "child_process";
import { existsSync, statSync } from "fs";
import { rm } from "fs/promises";
import { TMP_DIR, sanitizeAndAssertTmpPath } from "../security/pathGuard.js";
import { libreofficeMutex } from "../security/loMutex.js";

const CONVERTER_NAME = "LibreOffice";
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

  // Extract jobId from path: /tmp/zenvort/<jobId>-output.<ext>
  const fileName = safeOutput.split("/").pop() ?? "";
  const jobId = fileName.replace(/^([^-+]+)-output\..+$/, "$1");

  const userInstall = `${TMP_DIR}/lo-profile-${jobId}`;

  // soffice outputs <input-base>.<outputFormat> into --outdir.
  // e.g. /tmp/zenvort/docx.docx → /tmp/zenvort/docx.doc (for docx→doc).
  // We compute that path and rename it to safeOutput after conversion.
  const inputBase = safeInput.split("/").pop()?.replace(/\.[^.]+$/, "") ?? "";
  const sofficeOutput = `${TMP_DIR}/${inputBase}.${outputFormat}`;

  const startTime = Date.now();

  // Serialize all LibreOffice conversions in this process
  await libreofficeMutex.runExclusive(async () => {
    await new Promise<void>((resolve, reject) => {
      const proc = spawn("soffice", [
        "--headless",
        "--convert-to",
        outputFormat,
        "--outdir",
        TMP_DIR,
        `--user-installation=${userInstall}`,
        safeInput,
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
        } else if (code === 1) {
          // LibreOffice sometimes exits 1 with a javaldx warning even when
          // the output file was written correctly. Check the output before rejecting.
          try {
            const stat = statSync(sofficeOutput);
            if (stat.size > 0) {
              console.warn(`[libreoffice] exit code 1 ignored — output file exists (${stat.size} bytes)`);
              resolve();
              return;
            }
          } catch {
            // fall through to reject
          }
          reject(new Error(`${CONVERTER_NAME}: Process exited with code 1 and no valid output. stderr=${stderr}`));
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
    }).then(async () => {
      // soffice outputs <input-base>.<outputFormat> into --outdir.
      // Rename it to the expected safeOutput path.
      if (existsSync(sofficeOutput)) {
        const { rename } = await import("fs/promises");
        await rename(sofficeOutput, safeOutput);
      }
    }).catch(async (err) => {
      if (existsSync(safeOutput)) {
        await import("fs").then((fs) => fs.promises.unlink(safeOutput).catch(() => {}));
      }
      throw err;
    });
  });

  // Clean up the per-job profile directory after conversion
  await rm(userInstall, { recursive: true, force: true }).catch(() => {});

  const duration = Date.now() - startTime;
  console.log(`${CONVERTER_NAME} converted ${inputFormat} → ${outputFormat} in ${duration}ms`);
}
