# Vice Heist — Stake staging acceptance matrix

**Status:** not executed against an authorized Stake staging session. This checklist must be completed with platform-issued test access before any real-money submission.

## Evidence required

Record the staging environment name, game version, frontend commit SHA, matching math/frontend artifact SHA-256 digests, test timestamp, jurisdiction, currency, bet amount (integer wallet micro-units), outcome ID, expected behavior, observed behavior, and redacted request/response traces. **Never commit session IDs, bearer tokens, wallet credentials, or personally identifying data.**

## Test matrix

| Area | Minimum staging verification | Pass evidence |
| --- | --- | --- |
| Session authentication | Valid session; expired/invalid session; rejected origin | Correct wallet/config or safe failure; no secret leakage |
| Base wagers | Each of the 13 configured bet levels | One debit per accepted wager; matching server book and round ID |
| Bonus buy | Each permitted bet level at 100× cost | Explicit confirmation; exactly one 100× debit; correct event playback |
| Wallet precision | Each platform-approved fiat/crypto currency and smallest supported amounts | Integer micro-unit arithmetic and correctly formatted balance; no float drift |
| Insufficient funds | Base and bonus amounts exceeding balance | Rejected without duplicate charge or spin |
| Round settlement | Win, zero-win, max-win, natural free spins, bonus buy | Server payout and events agree; final wallet balance reconciles |
| Interrupted play | Timeout before play response; disconnect during reveal; end-round failure | No automatic paid retry; reload/recovery resumes the correct round |
| Replay | Valid replay; malformed/unauthorized replay | Accurate non-wager replay; no balance mutation |
| Jurisdiction flags | Bonus disabled, turbo disabled, RTP hidden, session limits | UI obeys flags and server rejects forbidden requests |
| Bet limits | Minimum, maximum, off-step, out-of-range | UI and RGS reject invalid wagers |
| Accessibility and devices | Desktop and mobile browsers, keyboard, reduced motion | Controls usable, no blocking errors |
| Hosting and security | HTTPS, CORS, CSP, asset integrity, no embedded secrets | Production browser network/security audit |

## Release approval conditions

1. CI release validation and official SDK **format** checks pass for the exact submitted commit.
2. The two independently uploaded production packages match the recorded SHA-256 digests.
3. All relevant staging rows above are executed and signed off, with failures resolved and rerun.
4. Stake confirms the current required endpoints, package structure, math upload and replay expectations, supported currencies, and jurisdiction requirements.
5. Owner gives **explicit approval** for submission. Do not merge to `main` or deploy as a side effect.

Passing mock-RGS tests, 104 million sampled weighted rounds, and SDK format checks **does not** replace staging evidence or Stake certification.
