# docs-delta: launch verification

Verified 16 October 2026 (Asia/Saigon).

- Public Store: https://apify.com/reliable_quatrain/website-markdown-rag-change-feed
- GitHub: https://github.com/boyhoanghoi/docs-delta-apify
- Actor ID: `02Xe4XI3SVfP6CIka`; current build `0.2.1` / `JEeCyRoJhpPWXAOak` succeeded.
- Package version `0.2.0`; deployed source commit `8956044fe7c91b14c13fcb228e0341780a79b41d`.
- 46 meaningful Python unit tests passed in the standalone virtual environment.
- Official Apify CLI validated input, dataset and output schemas.
- Active single pay-per-event price: USD 0.003 per `page-processed`.
- Unauthenticated public Actor metadata returned isPublic=true; the public Store URL returned HTTP 200 with the expected title.

## Cloud integration checks

The incremental-indexing release was checked with `examples/first-run.json`,
512 MiB memory, a 180-second timeout and a USD 0.01 maximum Actor charge per run.

1. Run `8OHzluBbB5cKyh6CO` succeeded on build `JEeCyRoJhpPWXAOak`: 2 dataset
   rows, 2 `page-processed` events, 37 chunk UPSERT operations and 0 REMOVE
   operations. Every operation belonged to a saved source page; nested chunks
   and operations added no custom paid events.
2. Run `5UqA8yaoqvcLlXX5M` reused its SNAPSHOT with `changedOnly: true`: 2 unchanged
   pages filtered, 0 dataset rows, 0 paid events and 0 chunk operations.
   The returned snapshot matched the previous baseline exactly.

Final run metadata, dataset rows, SUMMARY and CHUNK_OPERATIONS were compared
after each run. Public Store HTTP 200 and the new CHUNK_OPERATIONS documentation
were also verified. The existing single USD 0.003 `page-processed` price and
public visibility were preserved. No outreach was sent.

## Earlier cloud integration checks

1. Run `MpffqgyiPZMmSQ9uK` succeeded: 2 dataset rows, 2 `page-processed` events.
   Two real public documentation URLs produced 37 nested chunks; chunks did not add billing events.
2. Run `TZ224or8hFwrUA7Xb` reused SNAPSHOT with changedOnly=true: 2 unchanged pages filtered, 0 dataset rows and 0 paid events.
   Prior snapshot entries were retained; no page removals were inferred.

Observed platform usage for these small owner-run samples: USD 0.0006978046732876037 and USD 0.0006649296556545628. These measurements do not predict all sources, batch sizes or customer costs.

Owner tests are not customer revenue. No first customer or payout is claimed. No promotional messages were sent.

## First-user kit update — 16 October 2026

The [two-page walkthrough](FIRST_RUN.md), observed-run image, [English/Vietnamese
post drafts](LAUNCH_POSTS.md), [7-day experiment](ACQUISITION_7_DAYS.md), tracking
CSV and validated first-run input are public in the GitHub repository. The
image's 2-page / 37-chunk figures were checked against the recorded owner-run
output. The image was visually inspected and its public PNG URL verified.

The Store README update was uploaded from commit `958341f`. After temporary
API connection timeouts, the recovered public Actor API confirmed successful
release `0.1.2` / `6zMU7RfTzcqkSI9bA` as the latest tagged build on 16 October 2026.
The new image URL was observed in the public Store HTML.
No runtime code or pricing change was requested and no additional paid run was
started for this documentation update. No posts, replies or direct messages
were sent to any community or person.

## Artwork and recurring workflows

Upload `assets/brand/icon-512.png` under [Publishing / Display information](https://console.apify.com/actors/02Xe4XI3SVfP6CIka/publication) to replace the default Actor icon. The PNG and editable SVG are in the repository.

[Vietnamese workflow guide](WORKFLOW_COOKBOOK_VI.md) explains explicit state handoff. A fixed scheduled input does not automatically reload state. [Market research](MARKET.md) records observed demand, alternatives and scope differences.
