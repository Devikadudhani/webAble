import { copyFileSync, mkdirSync } from "node:fs";

mkdirSync(new URL("../app/vendor/", import.meta.url), { recursive: true });
for (const filename of ["axe.min.js", "LICENSE"]) {
  copyFileSync(
    new URL(`../node_modules/axe-core/${filename}`, import.meta.url),
    new URL(`../app/vendor/${filename}`, import.meta.url),
  );
}
