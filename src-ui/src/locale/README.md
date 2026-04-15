# i18n / Localization Setup

This directory holds Angular locale extraction files (`.xlf` / `.xliff`).

## Setup steps (not yet performed)

1. Add `@angular/localize` to the project:
   ```
   ng add @angular/localize
   ```
   This patches `angular.json`, adds a polyfill import to `main.ts`, and installs
   the package.

2. Mark translatable strings in templates:
   ```html
   <span i18n="@@my.translation.id">Hello</span>
   ```
   and in TypeScript:
   ```ts
   import { $localize } from '@angular/localize';
   const msg = $localize`:@@my.translation.id:Hello`;
   ```

3. Extract messages into an XLIFF file:
   ```
   ng extract-i18n --output-path src/locale
   ```
   This produces `messages.xlf` (XLIFF 1.2 by default).

4. Copy and translate per locale, e.g. `messages.fr.xlf`, then configure
   `angular.json` with `i18n.locales` and `build.configurations.<locale>`.

5. Build per locale:
   ```
   ng build --localize
   ```

## Notes

- Do NOT manually edit `angular.json` for i18n until `ng add @angular/localize`
  has been run, as the schematic inserts required boilerplate automatically.
- XLIFF 2.0 can be selected with `--format xliff2` on the extract step.
