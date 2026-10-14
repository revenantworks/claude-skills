# Names method

Read in `names` mode. One file per culture under `<bible>/names/<culture>.md`. The same rules generate names and test them; a generator with no test, or a test with no generator, drifts.

## Contents

- Rule file fields
- Generate
- Test
- Pronunciation key
- Worked example (invented culture)

## Rule file fields

```yaml
---
culture: <id>
level: soft
onsets: [k, t, v, r, s, l]          # sounds that may start a syllable
nuclei: [a, e, i, o]                # vowels and vowel pairs
codas: [n, r, l, ""]                # sounds that may end a syllable ("" = open)
shapes: ["CV", "CVC", "CV.CVC"]     # syllable patterns a whole name may take
forbidden: ["kk", "aa", "sr"]       # clusters never allowed, anywhere
folds: {c: k, y: i}                 # spellings treated as one sound for variant tests
patterns: ["<given> of <place>"]    # how full names are built
---
```

## Generate

1. Build candidates only from the rule file's sounds and shapes.
2. Drop nothing silently: run each candidate through **Test**; show failures with `NAME-RULE` and the rule broken.
3. Offer the passing set with a pronunciation for each.

## Test

A name passes when all hold:

1. It parses into the culture's `shapes` from its `onsets`, `nuclei` and `codas`.
2. It contains no `forbidden` cluster.
3. After `folds`, it is at edit distance 3 or more from every existing name in the bible (any culture). Distance 1–2 is `NAME-VARIANT` with the near name shown; the user decides.

## Pronunciation key

Each culture file ends with a table: `| spelling | say it | stress |`. Every name used in voiced, narrated or sung text needs a row; `audit` reports a missing one as `FIELD-MISSING`. The key is plain data a narration or voice brief can read.

## Worked example (invented culture)

Rules: onsets `k t v r`, nuclei `a e i`, codas `n l ""`, shapes `CV.CVC`, forbidden `ii`, folds `c → k`.

- `Kaelen` → fails shape (`ae` is not a nucleus): `NAME-RULE`.
- `Kelin` → passes; existing name `Kalin` sits at distance 1: `NAME-VARIANT`, shown beside `Kalin`.
- `Tavel` → passes; nearest existing name at distance 3. Offered.
