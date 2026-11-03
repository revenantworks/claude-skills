# Fee rules — what a listed price leaves out

Last verified: 2026-11-03

Calendar surface, 60-day cadence, re-verified by `faretender refresh`. Rates and rules change; never quote a city tax rate from this file or from memory. Read the rate from the offer or the city's official page, and cite it.

## Contents

- United States
- Elsewhere
- Charges no price shows
- Per-source notes
- Drop rules (watch)
- Sources

## United States

- The FTC Rule on Unfair or Deceptive Fees took effect on 2025-05-12. It covers short-term lodging (hotels, motels, short-term rentals) and live-event tickets.
- A covered business must show a total price with every charge it knows and can calculate upfront, including mandatory fees such as resort or destination fees.
- It may leave out only government charges (taxes), shipping and optional add-ons. Taxes left out must still be disclosed, with amount and purpose, before payment.
- So for a US hotel, **add the room tax and any local occupancy tax** to the shown price. Parking is in the total only when it cannot be avoided; otherwise add it when the user has a car.

## Elsewhere

- Many cities charge a tourist or city tax per person per night, often paid at the property. Some booking sites show it and some do not, for the same hotel. Always check each source's breakdown.
- When a source shows no city tax, look up the city's official rate and add it, marked with its source.

## Charges no price shows

Found in reviews, not in offers (`fees` entry): parking, safe or in-room fees, minibar sensor charges, deposits and holds, early check-in and late check-out, pet fees, card surcharges.

## Per-source notes

Record here, with a date, any pattern seen in a connector's output, for example which source includes city tax. Empty at 1.0.0.

## Drop rules (watch)

- Hotels: only refundable rates can be rebooked without loss. Rebook first, cancel second.
- Flights: on most changeable US main-cabin fares a lower fare returns airline credit, not cash. Basic economy fares usually cannot be changed. Read the fare rules in the confirmation. (Inferred from general knowledge; refresh should confirm per airline.)
- Car rentals: pay-later rates can be rebooked and cancelled; prepaid rates often carry a cancel fee.

## Sources

| Claim | Source | Checked |
|---|---|---|
| FTC fee rule scope, total price, three exclusions, effective date | [FTC, Rule on Unfair or Deceptive Fees FAQ](https://www.ftc.gov/business-guidance/resources/rule-unfair-or-deceptive-fees-frequently-asked-questions) | 2026-11-03 |
| Same, secondary | [Fenwick FAQ on the FTC fee rule](https://acquia.fenwick.com/insights/publications/the-ftc-rule-on-unfair-or-deceptive-fees-faqs-and-guidance) | 2026-10-31 |
| Effective 2025-05-12 for live events and short-term rentals | [TechCrunch](https://techcrunch.com/2025/05/05/ftc-bans-hidden-fees-for-live-events-and-short-term-rentals-effective-may-12/) | 2026-10-31 |

The FTC row is primary since 2026-11-03.
