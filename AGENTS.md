# Agent Instructions
## Browser Testing and Lower-Cost Execution

- Never perform browser-based testing unless the user explicitly requests browser testing for the current task. A general request to implement, test, verify, commit, push, or deploy is not browser-testing authorization.
- This restriction includes interactive and headless browser checks, Playwright, Chrome/in-app browser automation, browser smoke tests, browser screenshots for validation, and browser UI/end-to-end tests. Keep explicitly requested browser checks minimal and bounded. Targeted non-browser unit, widget, API, static, and command-line checks remain allowed.
- The coordinating agent must delegate all commit and push execution, and every explicitly requested browser test, to a lower-cost subagent. This is mandatory even for one repository or a small change; the coordinator must not execute those operations itself.
- Use `gpt-6-luna` with the model set explicitly. Use `gpt-6-sol` only if Luna is unavailable or insufficient and Sol is a lower-cost option than the coordinating model. Never silently inherit or use the coordinating model for these operations.
- Reuse a lower-cost agent where practical, provide only the necessary context, and keep one Git writer per repository. A delegated lower-cost agent executes its assigned work directly; this rule does not require recursive delegation.
- The coordinating agent retains planning and review, verifies reported commit IDs/remote branches and test evidence, and summarizes results without repeating browser tests.
- If no suitable lower-cost model or delegation tool is available, report the limitation and wait for user direction for the affected operations. Do not silently fall back to the coordinator.
- Existing authorization, branch, validation, and secret-handling rules still apply. These instructions do not themselves authorize any commit, push, deployment, or browser test.
