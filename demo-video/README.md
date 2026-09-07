# Backfill demo video

This directory is the machine-owned, caption-first Remotion source for the Agents for Humans hackathon demo.

## Evidence posture

The video does **not** simulate a new live transaction. Its provider-run scene is explicitly labeled as a reconstruction of the verified August 26, 2026 E5 run from preserved controlled Gmail/Calendar evidence and documented terminal facts.

The source intentionally does not contain private OAuth files, tokens, personal inbox history, or private ChatGPT content. The reconstructed cards use bounded labels such as Candidate C1 rather than publishing private account details.

Verified facts used by the video:

- one controlled Backfill offer was sent for the Aug 27, 2026 4:00–4:30 PM ET test slot;
- the consenting recipient replied with exact first-line `ACCEPT`;
- the recovered booking still exists in the dedicated `Backfill Demo` calendar;
- Backfill sent a provider-verified confirmation;
- the preserved run record reached `COMPLETED_RECOVERED`;
- test appointment value was $85 and is **not** project revenue;
- public CI run `33181027058` provides 30-test, Strands smoke, and checksum evidence.

Any later use of synthetic terminal visuals must remain labeled as reconstruction unless original terminal footage is independently recovered.

## Timing

The composition is 4:15 at 30 fps and follows the existing five-part narration spine:

1. 0:00–0:35 — problem / audience;
2. 0:35–1:05 — architecture;
3. 1:05–2:55 — verified provider-run replay;
4. 2:55–3:35 — correctness / CI;
5. 3:35–4:15 — close / evidence boundaries.

The visual cut is caption-first, so it remains understandable without narration audio. Narration can be added later if an authorized machine audio route is available or if a bounded human voice recording is chosen for presentation quality.

## Commands

```bash
npm install
npm run verify
npm run studio
npm run render
```

`npm run verify` type-checks and bundles the composition. `npm run render` writes `out/backfill-demo.mp4`.

## Claim boundaries

Do not describe the verified run as a production customer deployment or the $85 test value as revenue. Do not claim AgentCore/Bedrock deployment. The verified offer landed in Gmail Spam, which remains a real deliverability risk for a production pilot.
