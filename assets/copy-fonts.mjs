/*
 * Copies the self-hosted typefaces next to the compiled stylesheet - see docs/patterns/visual-identity.md.
 *
 * "assets/css/tailwind.css" imports each face's fontsource stylesheet, and Tailwind inlines those but
 * leaves their "url(./files/...)" as written. Resolved against "static/dist/tailwind.css", that is
 * "static/dist/files/", which is where this puts the font files. Run by "yarn build:css" and
 * "yarn watch:css" before Tailwind, so the stylesheet never ships pointing at fonts that are not there.
 *
 * Node rather than "cp" in package.json, so it runs on Windows too.
 */
import { cpSync, mkdirSync } from "node:fs";

const FACES = ["young-serif", "atkinson-hyperlegible", "reenie-beanie"];
const TARGET = "static/dist/files";

mkdirSync(TARGET, { recursive: true });
for (const face of FACES) {
    // Upright only: the italics are in the package but no stylesheet imports them.
    cpSync(`node_modules/@fontsource/${face}/files`, TARGET, {
        recursive: true,
        filter: (path) => !path.includes("-italic."),
    });
}
