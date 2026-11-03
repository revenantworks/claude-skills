# Trigger Evals — revenantworks-hearth-faretender

- Provenance: revenantworks-hearth-faretender · v1.0.0 · derived 2026-10-31. Authored, not run; the cold judge is owed.
- Counts: 24 queries (16 should, 8 should-not, 4 pairs), judged cold against name + description only.

| # | Query | Should trigger? | Why |
|---|---|---|---|
| 1 | "Compare the Cosmopolitan and the Bellagio for March 3 to 6, two adults, with every fee in." | ✅ yes | compare, core case |
| 2 | "What will this Marrakesh riad really cost once the city tax is added?" | ✅ yes | compare, real total |
| 3 | "Which of these three hotels has hidden fees people complain about?" | ✅ yes | fees |
| 4 | "Does the Wynn charge a resort fee and how much is parking?" | ✅ yes | fees, resort fee |
| 5 | "faretender watch" | ✅ yes | watch, named |
| 6 | "Did my Lisbon hotel get cheaper since I booked it?" | ✅ yes | watch, plain words |
| 7 | "Check every morning whether my refundable booking dropped." | ✅ yes | watch from a schedule |
| 8 | "Add my Tokyo trip to my calendar, flights and check-in." | ✅ yes | calendar |
| 9 | "When does free cancellation end on my Paris booking? Put it on my calendar." | ✅ yes | calendar, deadline |
| 10 | "My Lufthansa flight from Frankfurt landed 4 hours late, am I owed money?" | ✅ yes | claim, EU261 |
| 11 | "United cancelled my flight, can I get a refund instead of credit?" | ✅ yes | claim, US DOT |
| 12 | "Draft a compensation claim for my delayed easyJet flight." | ✅ yes | claim draft |
| 13 | "faretender" | ✅ yes | bare invocation |
| 14 | "Is the refundable rate worth the extra for this hotel?" | ✅ yes | compare, refundable premium |
| 15 | "Compare these two rental car quotes with airport fees and the toll pass." | ✅ yes | compare, car |
| 16 | "This Booking.com quote looked cheap but my bill was higher. What did it leave out?" | ✅ yes | audit |
| 17 | "Should I pay cash or use my Chase points for this hotel?" | ❌ no | Points, travel-hacking-toolkit |
| 18 | "Book the cheaper room and cancel my old one for me." | ❌ no | Booking, never done; pair with 6 |
| 19 | "Set up a daily cron routine with retries and a kill switch for my travel checks." | ❌ no | Schedule design, agentwright; pair with 7 |
| 20 | "Is the LetsFG connector safe to install?" | ❌ no | Vetting, trustwarden; pair with 1 |
| 21 | "What are the best neighbourhoods to stay in Lisbon?" | ❌ no | Place research, not cost |
| 22 | "Write me a packing list for a week in Iceland." | ❌ no | Off-topic travel task |
| 23 | "Which transfer partner gets the most value from Amex points to Tokyo?" | ❌ no | Points, travel-hacking-toolkit; pair with 2 |
| 24 | "Track my monthly subscriptions and tell me which to cancel." | ❌ no | Life task, not travel |

**Edge notes.** The sharpest pair is 6 against 18: the same booking, one asks for a check, the other for a purchase. Misses on the yes-set mean the triggers need pushier wording; fires on the no-set mean the boundary sentence needs tightening.
