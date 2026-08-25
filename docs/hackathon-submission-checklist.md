# Agents for Humans Hackathon — Submission Checklist

Last verified against the official Devpost rules/FAQ: 2026-08-25.

Official rules: https://agentsforhumans.devpost.com/rules
Official FAQ: https://agentsforhumans.devpost.com/details/faqs

## Time-critical

- [ ] Request up to **$50 in AWS Promotional Credits** by **September 11, 2026 at 12:00 PM PT**, while supplies last. Official request form: https://forms.gle/6sjzKiX6bKUMA5NEA
- [ ] Submit the final hackathon entry by **September 14, 2026 at 5:00 PM PT**.
- [ ] Keep any awarded promotional credits within their terms; the official rules state these credits expire **October 31, 2026**.

## Required submission pieces

- [x] New AI-agent project built during the submission period.
- [x] Strands Agents SDK used in the project.
- [x] Public source repository.
- [x] MIT license present and recognized by GitHub.
- [x] README present.
- [x] Architecture diagram present.
- [ ] Text description explaining features and functionality.
- [ ] Public demo video, maximum **5 minutes**, uploaded to YouTube or Vimeo.
- [ ] Video demonstrates the working project end to end.
- [ ] Video pitch states: the problem, who it is for, and why it matters.
- [ ] AWS Builder ID entered in the submission.
- [ ] Working project access/testing instructions available to judges through the end of judging.
- [ ] Choose exactly one track for this submission.

## Backfill-specific proof target

Before recording the final demo, prefer a fresh valid E5 run in which the real `BackfillApplication` owns offer sending, reply interpretation, booking, provider verification, confirmation, and terminal completion. Do not use the invalid duplicate-email attempt as evidence.

The current blocker is the one-time Google Desktop OAuth authorization documented in `docs/desktop-oauth-checklist.md`. No additional live email or booking should be attempted before the actual runtime has those credentials.

## Submission-quality opportunities

These are optional rather than blockers:

- A live demo link can strengthen the Technical Implementation score.
- Amazon Bedrock AgentCore is encouraged but not required; the rules state it can strengthen Technical Implementation.
- Public posts on `builder.aws.com` about the build journey can earn bonus judging points, subject to the current official rules.

## Judging lens

Stage Two uses five equally weighted criteria: Technical Implementation, Design, Potential Impact, Creativity & Originality, and Presentation. Backfill should therefore preserve not only technical correctness but a coherent end-to-end product story that visibly solves cancelled-appointment recovery for a real audience.

## Verified repository state on 2026-08-25

- Public repository: `84dnnvbdvp-debug/backfill`.
- GitHub recognizes the repository license as MIT.
- Clean GitHub Actions run has passed the canonical 30-test suite and Strands smoke harness.
- Dedicated Google Calendar and Gmail provider mutation/readback have reached E4.
- E5 remains unverified pending the actual runtime OAuth checkpoint.
