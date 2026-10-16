# Model weights — the executable risk is in the file, the licence risk is in the card

> **Last verified: 2026-10-13.** Calendar surface, 90 days (`volatile.json`). The Civitai and
> Hugging Face API fields below were read live in the session behind observation 0428 (a ComfyUI
> install: 11 pickle files, five custom-node folders, one LoRA whose two cards disagreed).
> `trustwarden refresh` re-reads both APIs and the three weights readers' docs, then restamps.

Read when a candidate holds weight files: `.pkl`, `.pickle`, `.pt`, `.pth`, `.ckpt`, a `.bin`
that is a torch zip, `.safetensors` or `.gguf`. That covers a model download, a ComfyUI or other
custom-node folder that ships models, and a skill or plugin with a model in its assets.

## Contents

- What the script reads, by format
- The pickle allow-list
- Second readers for weights
- Tracked versus generated
- Licence per weight
- Terms

## What the script reads, by format

| Format | Class in the ledger | What `trust_vet.py` does | Verdict effect |
|---|---|---|---|
| `.safetensors` | `weights`, non-executable | Checks the header: an 8-byte little-endian length, then that many bytes of JSON | READ. A header that does not parse is `weights-bad-header`, UNREAD binary, HOLD |
| `.gguf` | `weights`, non-executable | Checks the `GGUF` magic | Same as safetensors |
| `.pkl`, `.pickle`, legacy `.pt` and `.pth` | `weights-pickle`, executable | Parses every opcode with `pickletools` and lists every global the load would import. It never loads the file | READ when the bytes are whole pickle streams to the end; anything else is `pickle-unparsed`, UNREAD, HOLD |
| torch zip (`.pt`, `.pth`, `.ckpt`, `.bin`) | `weights-pickle`, executable | Opens the zip's directory (nothing is extracted) and scans each inner `.pkl` member | As above, per member. A `.py` or `code/` member is TorchScript, which `torch.jit.load` runs: `torchscript-code`, HOLD |
| a `.bin` that is not a torch zip | `bytecode` | Unchanged: unread | UNREAD, HOLD |

Weights are read at any size: the 1 MB text cap does not apply to them. A legacy torch file
(the pre-1.6 raw layout: pickles followed by raw storage bytes) does not end on a pickle, so it
stays UNREAD. Convert it to safetensors in a sandbox, or record a weights reader that read it.

The auto kind is `weights` when the tree holds weight files and no scripts, `.mcp.json`,
`SKILL.md`, plugin or Action markers. A ComfyUI custom-node folder holds code too: vet it under its
code kind, and the weights inside it are still scanned. Pass `--kind weights` to say so outright.

## The pickle allow-list

A pickle can import any callable and run it on load. The scan sorts every import into one of three
rules:

- **`pickle-dangerous-global` (FAIL).** A module from `os`, `posix`, `nt`, `subprocess`, `sys`,
  `socket`, `shutil`, `runpy`, `importlib`, `ctypes`, `pickle`, `marshal`, `operator`, `io`,
  `pathlib` and the like, or a builtin such as `eval`, `exec`, `open`, `getattr` or `__import__`.
  Nothing lowers it, `--allow-global` included.
- **`pickle-global-unknown` (HOLD).** Anything outside the allow-list: tensor rebuilders and
  storages (`torch._utils._rebuild_tensor_v2`, `torch.FloatStorage`, dtypes), numpy
  (`numpy.core.multiarray._reconstruct`, `numpy.ndarray`, `numpy.dtype`, `numpy.dtypes.*DType`),
  `collections.OrderedDict`, `_codecs.encode`, `copyreg._reconstructor`, and the harmless
  builtins (`set`, `frozenset`, `slice`, `complex`, `bytearray`, `object`). A reader looks up what
  the import does. If it only builds data (a scipy sparse matrix, say), the user re-runs with
  `--allow-global module.name`, and the report lists that import as the user's call.
- **`pickle-global-unresolved` (HOLD).** An import whose name is built at load time (a
  `STACK_GLOBAL` fed by anything but plain strings, or the copyreg extension registry). The scan
  follows strings through the memo, so a name pushed, memoized and fetched back is still named.

Names come from the candidate, so the report shows only identifier-shaped names; anything else
reads `<non-identifier name>`.

## Second readers for weights

A pickle read by trust_vet alone caps the verdict at CONDITIONAL, whatever the kind. The second
reader for weights is one of these, run by hand by the user, never installed by the skill, and
recorded with `--reader NAME=clean` or `--reader NAME=hits:N`:

| Reader | What it is |
|---|---|
| `fickling` (Trail of Bits) | Pickle decompiler and static analyser |
| `modelscan` (Protect AI) | Scanner for serialized model formats, pickle-based ones included |
| `picklescan` | Lists the globals a pickle imports, against its own dangerous list |

Their flags and exit codes were not read by the change that added them: read each tool's own
docs before a run, and `refresh` pins them here. Vet the reader itself with trustwarden first.

## Tracked versus generated

When the candidate is a git checkout, every ledger row carries `tracked` from `git ls-files`.

- An untracked `.pyc` or `.pyo` whose source `.py` is tracked was compiled on this host. Its row
  reads GENERATED and leaves the verdict, with a reason telling the user to remove those files
  before install.
- Any other untracked UNREAD row still holds. The reason says it is not in the SHA: it was made or
  downloaded on this host, often a model fetched at first run. Vet it as its own candidate.

Outside a git checkout, `tracked` is null and nothing changes.

## Licence per weight

The repo's LICENSE covers the code, not the weights. Every vet with weights adds the
`weights-licence` note and the `licence-per-weight` term. Then, for each weight:

    python scripts/trust_vet.py licence --civitai-id <id> --hf-repo <owner/name> --text <LICENSE file>

`--civitai-json` and `--hf-json` take a saved API response instead; at least one source is
needed. The two id flags make one read-only GET each to the public model APIs
(`civitai.com/api/v1/models/<id>`, `huggingface.co/api/models/<owner/name>`). They send no token
and nothing from the candidate. A failed read counts as an unknown source.

| Source | Field | Read as |
|---|---|---|
| Civitai | `allowCommercialUse` (a list, or one string on older models) | Empty or `None` = no commercial use. Any of `Image`, `RentCivit`, `Rent`, `Sell` = yes, and those rights are listed |
| Civitai | `allowNoCredit`, `allowDerivatives`, `allowDifferentLicense` | `false` adds a credit term, a no-derivatives restriction, a keep-this-licence restriction |
| Hugging Face | `cardData.license`, else a `license:` tag | An `nc` licence id or non-commercial wording = no. A known open licence = yes (`cc-by` adds credit). The OpenRAIL, Llama and Gemma families = yes under a use policy. `other` or an unknown id = unknown |
| Licence text | each line | Non-commercial wording = no. A revenue or user threshold (`licence-revenue-threshold`) or source-available terms (`licence-restricts`) are conditions, named by file and line |

| Result | Verdict |
|---|---|
| Every source that rules says yes, no conditions | PASS |
| Yes, with credit, a use policy or a threshold | CONDITIONAL, one term each |
| A source is unknown | HOLD (`licence-unknown`) |
| The sources disagree | HOLD (`licence-sources-disagree`); a reader settles it from the licence text, and the stricter reading wins until then |
| Every source that rules says no | FAIL for commercial use (`licence-no-commercial`) |

The text check is a pattern read. A line such as "commercial and non-commercial use permitted"
reads as a no, so a FAIL or HOLD that rests on the text is read by hand before anything is decided.

## Terms

| Term | Answers |
|---|---|
| `pickle-load` | Any READ pickle. Load with `torch.load(weights_only=True)` or convert to safetensors; a full unpickle runs whatever the file imports |
| `licence-per-weight` | `weights-licence`. Run the licence mode for each weight before use |
| `record` | Every licence PASS or CONDITIONAL. Keep each source, its value and the date read: a licence is a dated claim |
| `credit`, `use-restrictions` | The licence mode's conditions, as worded in its output |
