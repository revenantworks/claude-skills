# Task cards — the unit of delegated work

## Contents

- What a card is
- The shape
- Fields
- Writing a card that works
- The queue and its states

---

## What a card is

One self-contained unit of work: everything the model is given, plus the check
that decides whether the result is kept. A card is written once and can be
re-run, which is where the economics turn — the cost is in writing it, so a
card used once is usually a loss and a card re-run pays for itself.

**A card carries its own check.** That is what makes an unattended queue
possible: the runner never has to decide whether output is good, only whether
the check passed.

## The shape

Frontmatter for the machine, prose for the model:

```
---
target: path/to/the/file/it/writes
mode: unattended            # or interactive
check: <command that must pass>
expect: <what must be true of the result>
---
<the whole prompt the model receives>
```

## Fields

| Field | Meaning |
|---|---|
| `target` | The single file the unit writes. One file per card |
| `mode` | `interactive` (a check is recommended) or `unattended` (a check is required) |
| `check` | The command whose success decides the unit. **Required for `unattended`** |
| `expect` | What the check proves — a count, a schema, a floor. Written down so the report can say what was *not* proved |
| `schema` | Optional: a JSON schema to constrain generation, for structured output |
| `budget` | Optional token ceiling. Remember reasoning tokens count against it |

**Refuse an `unattended` card with no `check`, and say why**: nobody will read
the result before it is used, so the check is the only thing standing between
a wrong answer and a permanent record.

## Writing a card that works

Six rules, each of them the residue of a failed run.

1. **One file, one behaviour per card.** Given two target files at once the
   model spends its reasoning deciding which content belongs where instead of
   on the content. Measured: a two-target card burned most of its budget on
   that question.
2. **Paste the source it needs.** The model has no repository access. Anything
   it is not shown, it invents.
3. **Do not fight it about formatting.** A card that forbade code fences spent
   most of the model's reasoning on the rule. Strip fences afterwards; it costs
   one line and buys the whole budget back.
4. **State rules with their exception, or not at all.** A card demanding one
   declaration syntax produced unparseable code, because the rule was wrong in
   a context it did not carve out. An absolute rule is followed absolutely.
5. **Put every checkable property in the check, not the prose.** Asking for
   uniqueness in words produces duplicates; asking for it in a check produces
   a rejection you can act on. If a property can be counted, count it.
6. **Size the ask to the class.** Compositional requests can be large. Atomic
   ones saturate at a few dozen — partition them, or do them another way.
   `work-classes.md` has the measured numbers.

## The queue and its states

| State | Meaning |
|---|---|
| queued | Written, not yet run |
| running | In flight |
| done | Check passed; the result is kept |
| set aside | Check failed. The output, the reason and the model's reasoning are preserved for reading; the target is reverted |

**A set-aside unit is evidence, not rubbish.** The reason recorded there is
what tells you whether the card was wrong, the model was wrong, or the check
was wrong — and in the measured runs the card was at fault more often than the
model.

An unattended run stops on: an empty queue, a deadline, or a stop file. **It
does not loop.** A model choosing its own next task unattended is the failure
mode every other rule here exists to prevent.
