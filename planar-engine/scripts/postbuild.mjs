import fs from "fs";
import path from "path";
import { fileURLToPath } from "url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(__dirname, "../..");
const kernelSrc = path.join(repoRoot, "planar-engine/public/kernel.html");
const targets = [
  path.join(repoRoot, "public/planar/index.html"),
  path.join(repoRoot, "public/planar/kernel.html"),
  path.join(repoRoot, "public/disk.html"),
];

for (const dest of targets) {
  fs.mkdirSync(path.dirname(dest), { recursive: true });
  fs.copyFileSync(kernelSrc, dest);
  console.log(`[postbuild] kernel → ${path.relative(repoRoot, dest)}`);
}