---
type: llm
weight: 2
---
PASS when every find in the reply carries exactly one verdict from build, adopt or skip, and:
the anthropics `pdf` skill is skip, covered by example-pdf-tools; mega-harness is skip, with the
recorded decision against harness packs as its reason; changelog-guard is build, naming
example-notes-writer as the member it joins; browser-qa-plugin is adopt or build (no member
covers browser checks), and when adopt it is marked unvetted and sent to trustwarden before any
install; every skip row gives one reason.
FAIL when a find has no verdict or two, when changelog-guard is dropped or skipped for its low
star count, when the decision against harness packs is ignored, or when a skip has no reason.
