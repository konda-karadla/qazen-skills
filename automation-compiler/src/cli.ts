#!/usr/bin/env node
/**
 * Usage:
 *   tsx src/cli.ts <s5-output.json> [test-data.json] [--out-dir playwright/generated]
 *
 * <s5-output.json>   an S5 output object (see schemas/s5.schema.json)
 * [test-data.json]   optional flat key/value map used to fill {{placeholders}}
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

import { compileAutomationModel, outputFileNameFor } from "./compile.js";
import type { S5Output } from "./types.js";

const __dirname = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = join(__dirname, "..", "..");

function parseArgs(argv: string[]) {
  const positional: string[] = [];
  let outDir = join(REPO_ROOT, "playwright", "generated");
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--out-dir") {
      outDir = argv[++i];
    } else {
      positional.push(argv[i]);
    }
  }
  return { positional, outDir };
}

function main(): void {
  const { positional, outDir } = parseArgs(process.argv.slice(2));
  const [s5Path, testDataPath] = positional;
  if (!s5Path) {
    console.error("Usage: tsx src/cli.ts <s5-output.json> [test-data.json] [--out-dir DIR]");
    process.exit(1);
  }

  const s5: S5Output = JSON.parse(readFileSync(s5Path, "utf-8"));
  const testData: Record<string, unknown> = testDataPath
    ? JSON.parse(readFileSync(testDataPath, "utf-8"))
    : {};

  const source = compileAutomationModel(s5, testData);
  const fileName = outputFileNameFor(s5);

  mkdirSync(outDir, { recursive: true });
  const outPath = join(outDir, fileName);
  writeFileSync(outPath, source, "utf-8");
  console.log(`Compiled ${s5.script_id} (${s5.test_case_id}) -> ${outPath}`);
}

main();
