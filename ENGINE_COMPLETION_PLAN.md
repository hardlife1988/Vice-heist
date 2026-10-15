# ENGINE_COMPLETION_PLAN

## Objective

This plan maps the remaining Vice Heist checklist items to the engine requirements and implementation constraints for the feature/cyberpunk-assets branch. It is designed to keep all work isolated from main and to clarify what remains before release validation.

## Engine requirements covered

### 1) Statelessness
- The engine must be deterministic for a given round seed and game state snapshot.
- No hidden mutable state should be required to compute payouts beyond the supplied bet, mode, and result metadata.
- Frontend and Node consumers should be able to call the same helper methods without an active browser session.

Checklist coverage:
- Fix frontend payout calculation.
- Verify correct balance deductions, payouts, total-won display, bet sizes, and Bonus Buy cost.
- Ensure the browser loads the final validated math files rather than stale/experimental bundles.
- Compare event payout units against the credited payout, especially cents versus multipliers.

### 2) Modes
- The engine must support both base mode and bonus/buy mode with independent validation paths.
- Bonus Buy requires a 100× bet deduction and should use the bonus leave/trigger rules distinct from natural free spins.
- Base mode and bonus mode must not share the same LUT or payout assumptions without explicit validation.

Checklist coverage:
- Finish reel animation, staggered stops, final symbols, and Turbo mode.
- Test natural free-spin triggers, ten-spin counter, 2× multiplier, transitions, and payouts.
- Test Bonus Buy confirmation, 100× bet deduction, feature events, and payout.
- Decide whether free-spin retriggers should exist; they are not currently implemented.
- Verify Spin, bet +/- controls, Turbo, menu, sound, rules, and other visible buttons.

### 3) Math file format
- The engine should validate that the weighted LUT and the books JSON structure are aligned.
- Each book id must match the LUT payout bucket and weighted row.
- The payout multiplier must remain consistent across math bundles and the runtime integration layer.
- The engine must use the exact release bundle rather than stale or experimental artifacts.

Checklist coverage:
- Validate weighted LUT selection, book IDs, and Base/Bonus lookup alignment.
- Ensure the browser loads the final validated math files rather than stale/experimental bundles.
- Check final Stake Engine SDK compatibility, event schemas, books, and LUT format.
- Rebuild and validate the exact release math bundle; confirm weighted RTP near 96% for both modes.

### 4) Currency and payout conversion
- All payouts must be represented in consistent integer micro-units/cents before conversion to display currency.
- Frontend/wallet conversions must not directly credit a raw multiplier as money without multiplying by the actual bet.
- The payout conversion must be symmetric and guarded for invalid or NaN values.

Checklist coverage:
- Fix frontend payout calculation.
- Compare event payout units against the credited payout, especially cents versus multipliers.
- Verify correct balance deductions, payouts, total-won display, bet sizes, and Bonus Buy cost.

### 5) Win cap and guards
- The engine must enforce the 10,000× max win cap in both runtime math and payout conversion.
- Inputs like invalid multipliers, NaN values, negative numbers, and malformed books must be rejected safely.
- Bonus buy enforcement must never bypass the cap or create inconsistent totals.

Checklist coverage:
- 10,000× win cap.
- Guards for invalid input.
- Fix frontend payout calculation.
- Handle insufficient funds, repeated clicks, reloads, and missing data.

## Checklist mapping

### Completed / already validated
- Implemented 20 paylines, Wild substitutions, Scatter payouts, 10 free spins, 2× free-spin multiplier, 100× Bonus Buy, and 10,000× win cap.
  - Engine mapping: stateless math, modes, cap logic, bonus buy rules.
- Separated natural free-spin and purchased-bonus reel distributions.
  - Engine mapping: mode isolation.
- Passed evaluator unit tests and math bundle validation.
  - Engine mapping: math file format + validation path.
- Ran million-spin stress tests and denomination audit.
  - Engine mapping: cap, mode consistency, wallet math validation.

### Priority 1 — Frontend / math integration
- Fix frontend payout calculation. In static/game.js, centsToCash(book.payoutMultiplier || 0) is currently credited directly as money. Verify conversion and multiply the decoded win multiplier by state.bet before crediting balance.
  - Requirement mapping: currency conversion, statelessness, payout guards.
- Verify correct balance deductions, payouts, total-won display, bet sizes, and Bonus Buy cost.
  - Requirement mapping: currency conversion, modes, payout math.
- Validate weighted LUT selection, book IDs, and Base/Bonus lookup alignment.
  - Requirement mapping: math file format, mode validation.
- Ensure the browser loads the final validated math files rather than stale/experimental bundles.
  - Requirement mapping: exact release math bundle, stateless engine validation.
- Compare event payout units against the credited payout, especially cents versus multipliers.
  - Requirement mapping: micro-unit conversion, guard logic.

### Priority 2 — Finish gameplay
- Finish reel animation, staggered stops, final symbols, and Turbo mode.
  - Requirement mapping: mode behavior and UI layer.
- Test natural free-spin triggers, ten-spin counter, 2× multiplier, transitions, and payouts.
  - Requirement mapping: mode-specific payout rules.
- Test Bonus Buy confirmation, 100× bet deduction, feature events, and payout.
  - Requirement mapping: bonus-buy mode contract.
- Decide whether to implement the described BOOK expanding-symbol feature or remove that claim; rerun math validation if implemented.
  - Requirement mapping: release bundle correctness and feature scope.
- Decide whether free-spin retriggers should exist; they are not currently implemented.
  - Requirement mapping: valid engine mode scope and payout contract.
- Verify Spin, bet +/- controls, Turbo, menu, sound, rules, and other visible buttons.
  - Requirement mapping: runtime controls, not engine math.
- Handle insufficient funds, repeated clicks, reloads, and missing data.
  - Requirement mapping: guard clauses and state stability.

### Priority 3 — Visual design
- Finalize large edge-to-edge symbols, centered VICE HEIST logo, right control rail, and bottom HUD.
  - Requirement mapping: presentation only.
- Test desktop, tablet, and mobile layouts.
  - Requirement mapping: UI QA.
- Finish sound effects, mute, bonus effects, and win celebrations.
  - Requirement mapping: UX polish.
- Make rules and paytable accurately describe actual game behavior.
  - Requirement mapping: documentation and feature truthfulness.
- Polish loading, error, and empty states.
  - Requirement mapping: guard/UX handling.

### Priority 4 — Validate and launch
- Check final Stake Engine SDK compatibility, event schemas, books, and LUT format.
  - Requirement mapping: exact engine contract and math file format.
- Rebuild and validate the exact release math bundle; confirm weighted RTP near 96% for both modes.
  - Requirement mapping: math file format and validation.
- Run automated tests and complete browser end-to-end QA.
  - Requirement mapping: system verification before merge.
- Review performance, accessibility, console errors, and security.
  - Requirement mapping: release readiness.
- Clean temporary files and decide whether to archive large test logs.
  - Requirement mapping: repo hygiene.
- Test a preview without replacing the live GitHub Pages site.
  - Requirement mapping: deployment safety.
- Review PR #1, merge the feature branch into main only after approval.
  - Requirement mapping: branch governance, not engine code.
- Deploy, verify production, and document rollback.
  - Requirement mapping: release operations.

## Recommended execution order
1. Fix payout conversion and add regression tests for multiplier × bet crediting.
2. Validate book/LUT file alignment and mode-specific bundle selection.
3. Finish gameplay and controls.
4. Complete responsive visual polish.
5. Validate release bundle and Stake Engine compatibility.
6. Run browser QA, preview, then promote only after approval.

## Notes
- This branch remains isolated from main.
- The engine must remain deterministic and compatible with both Node and browser consumers.
- The math bundle is the official contract: if the books or LUT format changes, all payout assumptions must be updated together.
- Do not merge or deploy the feature branch until final validation passes.

## Completion summary
The essential engine-level items are:
- safe payout conversion
- valid base/bonus mode separation
- consistent book-to-LUT matching
- win cap enforcement
- guard clauses for invalid numeric inputs
- exact product of bet × multiplier in integer micro-units or cents before display conversion

Once those are validated, the remaining checklist items become release and UX tasks rather than core engine corrections.
