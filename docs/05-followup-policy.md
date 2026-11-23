# 05 — Follow-Up Policy

Defaults below are the shipped policy. The operative values live in config (`followup_intervals_days`, `followup_max`); change them there, not in letters or prompts.

## The policy in one paragraph

After the first letter, send **at most 3 follow-ups** on a tightening-then-steady cadence: follow-up 1 waits **4 days** after the first letter, follow-up 2 waits **7 more days**, follow-up 3 waits **7 more days** — the touches land on days 4, 11, and 18, and the whole sequence is done inside roughly three weeks. The third follow-up is a short, polite closing letter. Every follow-up must carry **genuinely new content from a new angle**; a follow-up that repeats or resembles the previous letter is not a follow-up. After the third follow-up with no reply, stop permanently and mark the company accordingly.

## Rules

1. **Intervals: [4, 7, 7] days.** `followup_intervals_days` in config: element N−1 is the wait after the previous touch before follow-up N may be sent, counted from the last actual send date (first letter or previous follow-up) in the tracker's send log. The first follow-up comes quickly, while the recipient still remembers the first letter; the later waits stretch to a week so the sequence informs without pressing. See "Why this cadence" below.
2. **Maximum: 3 follow-ups.** `followup_max` in config. The tracker (`scripts/build_tracker.py`) flags any company at the maximum as "sequence complete, do not contact".
3. **New content, new angle, every time.** Acceptable new content: a new product line or range extension with a photo or catalogue update, a price band relevant to the recipient's category, a concrete seasonal or market-relevant item, a specific answer to something on the recipient's public site, how a comparable buyer uses the product, a relevant trade-show presence with an invitation to meet. Not acceptable: a bare reminder, a restatement or near-copy of the previous letter, or "just checking in" with nothing attached. The quality gate enforces the floor in code: bare-nudge phrases fail, and a follow-up whose wording largely overlaps the previous letter fails the similarity check (`scripts/quality_gate.py`, `check_followup`).
4. **The third follow-up is a closing letter.** One or two sentences: thank them, say plainly that you will close the file unless they want the information, and leave the door open. No new pitch, no pressure. A clear, low-cost way to say no is exactly what makes some recipients answer.
5. **Same thread discipline, fresh check first.** Before drafting, re-check the company: still in business, not acquired or rebranded, no reply or unsubscribe recorded since, not newly blocklisted or excluded. Any of those stops the follow-up. The record-based part of this check is also enforced in code at the moment of sending: `scripts/send_mail.py --followup` re-reads the feedback log and send state and refuses when a reply, unsubscribe, or bounce has landed since selection, when the recipient address is a customer-service or functional mailbox, when the maximum is reached, or when the applicable interval has not elapsed — eligibility is never trusted from selection time.
6. **Replies end the sequence.** Any reply, positive, negative, or out-of-office with a named alternate, moves the company out of the automated follow-up pool. Substantive replies are handled by a human (see the confirmation list in `AGENTS.md`).
7. **Never follow up with these — no exceptions:**
   - a company whose mail **hard-bounced** (the address is disproven; following up only damages the sending domain);
   - a company that **replied** (a human owns the conversation now);
   - a company that **explicitly refused** or **unsubscribed** — permanent: never contact them again under any address, not just "no follow-up";
   - a company whose first letter could only go to a **customer-service or functional mailbox** (support, returns, orders, press, careers and kin — see "useful email" in `docs/03-email-verification.md`); it goes back to enrichment to find a decision-maker instead;
   - an address labelled **`accept_all_unconfirmed`** or otherwise unverified (an accept-all domain can never confirm the mailbox exists, so it was not sendable in the first place and is never followed up).
8. **Follow-ups pass the same quality gate, plus the follow-up checks.** Same letter rules as first touches (`docs/04-letter-rules.md`), same recipient-label requirement (`docs/03-email-verification.md`), and they count toward the daily send cap (see config), shared with first touches.
9. **Platform and partner contacts follow the same policy.** Channel partners are not an exception channel for extra touches.

## Why this cadence

The numbers below are the published, large-sample benchmarks behind the [4, 7, 7] / 3-follow-up shape. All of them come from vendors that sell sending platforms or outbound services — they have a commercial interest in the results, their denominators differ, and none of them should be quoted as a promise. What is used here is only the direction on which independent datasets agree.

- **Follow-ups earn roughly half the replies.** Belkins, analysing 7.53 million cold emails, found emails 2–6 of a sequence contributed 58.6% of all replies, and the third email was the peak for meetings booked. A first-letter-only policy abandons about half the replies the sequence would have earned.
- **Short early intervals, a few touches, done in weeks.** Instantly's benchmark guidance is 4–7 touches spaced 3–4 days apart. OpenOutreach's open-source sequence uses two follow-ups at +3 and +5 working days. The shipped [4, 7, 7] sits inside that envelope: first follow-up fast (day 4), then weekly, 4 touches total including the first letter, finished by day 18 — the conservative end of the range, chosen because these are small B2B buyers and sender-domain reputation is a hard constraint.
- **Each touch must add something.** The same datasets show the reply curve is earned by new information and new angles, not by reminders; a content-free nudge mostly earns spam complaints. That is why rule 3 is a gate, not a suggestion.
- **A closing letter converts some of the silence.** Multi-step sequences across vendors consistently show the final "I will close the file" message pulling replies from people who were never going to answer a pitch — it offers a costless no.

The previous shipped policy (one flat 30-day interval, at most 2 follow-ups, roughly three months) spread the same touches so thin that recipients had forgotten the first letter before the follow-up arrived, and stopped before the touch the data says is the meeting peak. It was replaced for those reasons, not for fashion.

## Migration from the legacy flat interval

Older configs carry `followup_interval_days` (a single flat wait) instead of `followup_intervals_days`. The config loader (`scripts/_config.py`) folds the legacy key into a flat sequence of that interval repeated `followup_max` times, so an existing operator keeps exactly the cadence they configured. To adopt the shipped cadence, replace `followup_interval_days: 30` with `followup_intervals_days: [4, 7, 7]` and set `followup_max: 3` in `config/config.json`.

## Tracker fields

The follow-up tracker (`scripts/build_tracker.py`) computes, per company: last touch date, follow-ups sent, next eligible date (last touch + the applicable interval from the sequence), sequence status (in sequence, eligible, complete, stopped), and the reason for any stop. Trust the tracker over memory or inbox impressions.
