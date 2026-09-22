import assert from "node:assert/strict";
import { test } from "node:test";

import { compileAutomationModel, outputFileNameFor } from "../src/compile.js";
import type { S5Output } from "../src/types.js";

const s5Example: S5Output = {
  script_id: "SCR-TC-001",
  test_case_id: "TC-001",
  layer: "UI",
  automation_model: {
    setup: [{ type: "navigate", target: "/login" }],
    actions: [
      { type: "fill", locator: "role=textbox[name=Username]", value: "{{username}}" },
      { type: "fill", locator: "role=textbox[name=Password]", value: "{{password}}" },
      { type: "click", locator: "role=button[name=Login]" },
    ],
    assertions: [
      { type: "visible", target: "role=heading[name=Dashboard]", expected_value: true, test_case_id: "TC-001" },
    ],
  },
  assertions_plain: ["After valid login, the Dashboard heading must be visible (proves TC-001)."],
};

test("compiles navigate/fill/click/visible into valid-looking Playwright source", () => {
  const source = compileAutomationModel(s5Example, { username: "standard_user", password: "secret_sauce" });

  assert.match(source, /import \{ test, expect \} from '@playwright\/test';/);
  assert.match(source, /test\("TC-001", async \(\{ page \}\) => \{/);
  assert.match(source, /await page\.goto\("\/login"\);/);
  assert.match(source, /\.fill\("standard_user"\)/);
  assert.match(source, /\.fill\("secret_sauce"\)/);
  assert.match(source, /\.click\(\);/);
  assert.match(source, /toBeVisible\(\); \/\/ proves TC-001/);
});

test("leaves unresolved placeholders untouched when no test data is given", () => {
  const source = compileAutomationModel(s5Example);
  assert.match(source, /\.fill\("\{\{username\}\}"\)/);
});

test("visible with expected_value false compiles to not.toBeVisible", () => {
  const invalid: S5Output = {
    ...s5Example,
    test_case_id: "TC-LOGIN-001",
    script_id: "SCR-TC-LOGIN-001",
    automation_model: {
      setup: [{ type: "navigate", target: "/login" }],
      actions: [
        { type: "fill", locator: "role=textbox[name=Username]", value: "invalid_user" },
        { type: "click", locator: "role=button[name=Login]" },
      ],
      assertions: [
        { type: "visible", target: "role=alert", expected_value: true, test_case_id: "TC-LOGIN-001" },
        {
          type: "visible",
          target: "role=heading[name=Dashboard]",
          expected_value: false,
          test_case_id: "TC-LOGIN-001",
        },
      ],
    },
  };
  const source = compileAutomationModel(invalid);
  assert.match(source, /role=alert.*\)\)\.toBeVisible\(\)/);
  assert.match(source, /role=heading\[name=Dashboard\].*\)\)\.not\.toBeVisible\(\)/);
  assert.doesNotMatch(source, /Dashboard.*\)\)\.toBeVisible\(\)/);
});

test("quotes role name attributes that contain spaces", () => {
  const spaced: S5Output = {
    ...s5Example,
    automation_model: {
      setup: [],
      actions: [{ type: "click", locator: "role=button[name=Log in]" }],
      assertions: [
        { type: "visible", target: "role=heading[name=Sign in]", expected_value: true, test_case_id: "TC-001" },
      ],
    },
  };
  const source = compileAutomationModel(spaced);
  assert.match(source, /role=button\[name=\\"Log in\\"\]/);
  assert.match(source, /role=heading\[name=\\"Sign in\\"\]/);
});

test("output file name matches test_case_id", () => {
  assert.equal(outputFileNameFor(s5Example), "TC-001.spec.ts");
});

test("unsupported step/assertion types degrade to a TODO comment, never a crash", () => {
  const weird: S5Output = {
    ...s5Example,
    automation_model: {
      setup: [],
      // @ts-expect-error -- intentionally invalid type to exercise the default branch
      actions: [{ type: "hover", locator: "x" }],
      assertions: [],
    },
  };
  const source = compileAutomationModel(weird);
  assert.match(source, /TODO: unsupported step type 'hover'/);
});
