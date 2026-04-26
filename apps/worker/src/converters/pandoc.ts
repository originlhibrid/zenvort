/**
 * Pandoc — universal document converter.
 * Safe: spawn() with argument array. No shell interpolation.
 * Paths asserted inside /tmp/zenvort/.
 */

import { spawn } from "child_process";
import { existsSync } from "fs";
import { sanitizeAndAssertTmpPath } from "../security/pathGuard.js";

const CONVERTER_NAME = "pandoc";
const DEFAULT_TIMEOUT_MS = 60_000;

let pandocVersion: string | null = null;

async function getPandocVersion(): Promise<string> {
  if (pandocVersion !== null) return pandocVersion;

  const proc = spawn("pandoc", ["--version"]);
  let stdout = "";

  await new Promise<void>((resolve) => {
    proc.stdout.on("data", (d) => { stdout += d.toString(); });
    proc.on("close", () => resolve());
    proc.on("error", () => resolve());
  });

  const match = stdout.match(/(\d+\.\d+(?:\.\d+)?)/);
  pandocVersion = match ? match[1] : "0";
  return pandocVersion;
}

function getMarkdownFlag(version: string): string {
  const [major] = version.split(".").map(Number);
  return major >= 3 ? "-t md" : "-t markdown";
}

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
  const version = await getPandocVersion();

  await new Promise<void>((resolve, reject) => {
    // Pandoc uses "plain" for text output, not "txt"
    const pandocOutputFormat = outputFormat === "txt" ? "plain" : outputFormat;
    // Pandoc uses "markdown" as the input format alias (not "md")
    const pandocInputFormat = inputFormat === "md" ? "markdown" : inputFormat;

    // Select output flag: -t md for pandoc 3+, -t markdown for older versions
    const outputFlag = outputFormat === "md" ? getMarkdownFlag(version) : `-t ${pandocOutputFormat}`;

    const args: string[] = ["-f", pandocInputFormat];
    // Splice the combined flag correctly: outputFlag is already "-t markdown" or "-t md"
    const flagParts = outputFlag.split(" ");
    args.push(flagParts[0], flagParts[1]);
    args.push("-o", safeOutput, safeInput);

    const proc = spawn("pandoc", args);

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
