# Agents for Humans Hackathon — Submission Checklist

Last verified against the official Devpost rules/FAQ: 2026-08-26.

Official rules: https://agentsforhumans.devpost.com/rules
Official FAQ: https://agentsforhumans.devpost.com/details/faqs

## Time-critical

- [x] Request up to **$50 in AWS Promotional Credits** by **September 11, 2026 at 12:00 PM PT**, while supplies last. Submitted 2026-08-25; approval/credit remains pending and must not be counted as spendable until verified.
- [ ] Submit the final hackathon entry by **September 14, 2026 at 5:00 PM PT**.
- [ ] Keep any awarded promotional credits within their terms; the official rules state these credits expire **October 31, 2026**.

## Required submission pieces

- [x] New AI-agent project built during the submission period.
- [x] Strands Agents SDK used in the project.
- [x] Public source repository.
- [x] MIT license present and recognized by GitHub.
- [x] README present.
- [x] Architecture diagram present.
- [x] Paste-ready text description and submission copy exists in `docs/final-devpost-copy.md`.
- [x] Required pre-existing-work disclosure is explicitly included in `docs/final-devpost-copy.md`.
- [ ] Public demo video, maximum **5 minutes**, uploaded to YouTube or Vimeo.
- [x] Verified working end-to-end test-context flow exists for video capture: actual runtime offer → real `ACCEPT` → provider booking/verification → confirmation → `COMPLETED_RECOVERED`.
- [x] Video storyboard and privacy-safe capture checklist exist in `docs/hackathon-presentation-plan.md` and `docs/demo-recording-checklist.md`.
- [x] Timed ~4:15 narration exists in `docs/demo-voiceover-script.md`.
- [ ] AWS Builder ID entered in the submission.
- [x] Judge-safe local testing instructions exist in `docs/judge-testing.md`.
- [ ] Choose exactly one track in the final Devpost form. Intended track: **Professional Agents**.
- [ ] Final Devpost submission completed.

## Backfill proof state

### E3 — clean runtime

- Public repo: `84dnnvbdvp-debug/backfill`.
- Clean GitHub Actions has installed the pinned Strands SDK and passed the canonical suite plus Strands smoke harness.

### E4 — authenticated provider reality

- Dedicated Google Calendar and controlled Gmail mutation/readback verified.

### E5 — consenting end-to-end test context

Verified 2026-08-26 under the actual Backfill runtime:
- one offer sent,
- real consenting recipient replied exact `ACCEPT`,
- booking created and provider-verified in `Backfill Demo`,
- confirmation sent,
- workflow reached `COMPLETED_RECOVERED`,
- test recovered value recorded as 8,500 cents.

This is **not** a real business/customer recovery and **not** external revenue. E6 remains unverified.

## Known product-readiness risk

The verified offer landed in Gmail Spam. Treat this as a concrete deliverability risk for a real pilot. Do not rerun E5 merely to accumulate evidence and do not run artificial “warming” campaigns. See the bounded deliverability note in `docs/hackathon-presentation-plan.md`.

## Submission-quality opportunities

Optional rather than blockers:
- live demo link;
- Amazon Bedrock AgentCore deployment;
- builder.aws public build posts for eligible bonus points;
- a small real-business pilot if a consenting low-friction opportunity appears before submission.

Do not delay a coherent submission merely to chase optional extras.

## Judging lens

Stage Two uses five equally weighted criteria: Technical Implementation, Design, Potential Impact, Creativity & Originality, and Presentation. Backfill should therefore show the working recovery loop clearly, explain why deterministic authority matters, and preserve evidence/claim boundaries.

## Current verified repository state

- Public repository and MIT license verified.
- Current main is green in GitHub Actions.
- Canonical suite: 30 tests.
- Strands smoke harness passes.
- E5 test-context completion verified with independent Calendar/Gmail readback.
- Architecture diagram ready.
- Paste-ready Devpost copy ready.
- Pre-existing-work disclosure ready.
- Demo recording checklist ready.
- Timed demo narration ready.
- Judge testing instructions ready.
- Clean phone-readable final submission copy also exists in Drive as `Backfill — Final Devpost Copy v1.0`.
- Remaining required human work: record/upload <=5-minute video, enter AWS Builder ID, select Professional Agents, submit Devpost.
