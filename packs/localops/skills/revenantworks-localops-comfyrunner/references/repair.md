# Repair — a server that will not start, an extension that breaks, a model to clear

Read when ComfyUI will not start after an update, an extension fails to import or to update,
or a model or extension is about to be added for work that will be sold. Everything here is
read from files on disk first; the package's own Python is run only after the cause is named.

## Contents

1. Torch stack out of step after an update
2. Pinning the pair so it stays matched
3. Extensions: update traps and import failures
4. Code a node downloads at first use
5. Adding a model: licence, source, hash
6. Launch settings worth proposing on AMD

## 1. Torch stack out of step after an update

**Signature:** a Windows "Entry Point Not Found" dialog naming `torchvision\_C.pyd` (or any
`_C.pyd`) and a mangled `c10` symbol, at startup. The compiled extension was built against a
different torch than the one installed.

1. **Read versions from package metadata, not the interpreter.** List the
   `torch-*.dist-info`, `torchvision-*.dist-info` and `torchaudio-*.dist-info` folder names in
   the venv's `site-packages`. No Python needs to run, so a denied or crashing interpreter does
   not block the diagnosis.
2. **Check the pairing:** torchvision's minor version is torch's minor plus 15 (torch 2.14 pairs
   with torchvision 0.29). A mismatch names the broken pair.
3. **Find the index the stack came from.** A uv-managed install keeps it in the wheel cache:
   `wheels-v*/index/<hash>/torch/*.http` holds the download URL. A vendor build (a ROCm or
   device-specific wheel) must come from that index, never from PyPI.
4. **Forward fix first:** `uv pip install --dry-run` the matching torchvision (and its device
   package, when the vendor ships one) from that index with torch pinned to the installed
   version. A dry run that swaps only the torchvision packages is the fix; a pre-release build
   (`a0`) is acceptable when it is the only matched one, and is named as such.
5. **Rollback** only when no matched build exists: the previous set is often still in the cache,
   but `uv pip install --offline` cannot resolve it without the index listing, so it needs the
   index online.
6. **Verify:** import torch and torchvision, print both versions and the device name, and run
   one native op on the GPU (`torchvision.ops.nms` on two boxes). The import alone does not load
   every kernel.

Never edit the venv unasked; state the dry run's diff and get a yes.

## 2. Pinning the pair so it stays matched

A `uv.toml` in the ComfyUI package folder, the folder the manager runs `uv pip` from, holds
`constraint-dependencies` with the exact torch and torchvision versions. It applies to that
install only, survives a ComfyUI `git pull` (the file is untracked), and makes a torch-only
upgrade resolve to no change while refusing a mismatched torchvision. Prove it with three dry
runs: an upgrade of torch, an install of the old torchvision, and the package's own
requirements file.

It does not reach installs made with plain `pip` (ComfyUI-Manager's in-UI installer), and an
extension install run from the extension's own folder may not find it. Re-check the torch
version after each extension install. Re-pin both lines when the vendor ships a newer matched pair.

## 3. Extensions: update traps and import failures

- **An extension folder with no `.git`** (installed from an archive or a registry) can be
  "updated" by a manager that falls back to the parent project's URL: it runs `git init` with
  ComfyUI's own repository, fetches its whole history, and may carry a reset-hard fallback that
  would replace the extension's files. Signs: the extension shows ComfyUI's own version number,
  or `git -C <ext> remote get-url origin` names ComfyUI's repository. The fix is uninstall and
  reinstall from the manager's list, which clones the right repository. Never retry Update on a
  flagged folder.
- **A manager's extension list can show a cache folder** (`__pycache__`) as an extension.
  Removing it is harmless; Python rebuilds it.
- **One failing module can fail the whole package** when an extension's loader error handler is
  itself broken (it names an undefined variable, so the `except` raises). The traceback shows
  two exceptions: the real import error, then the handler's `NameError`. Fixing the handler line
  lets the loader skip the one module and load the rest; say that the local patch makes the
  checkout differ from its pinned commit.
- **`triton` is not available on Windows with an AMD card.** A node that imports it fails at
  import; the rest of the package should load once the loader skips it. comfy-kitchen reports
  the triton backend unavailable and uses its `hip` backend, which is expected.
- **Deprecation warnings about `/extensions/core/*.js`** come from an extension's browser code,
  not the HTTP API this skill calls. They break that extension's widgets only when the front end
  drops the file; the fix is the extension author's.

## 4. Code a node downloads at first use

Some nodes fetch Python from a model host on first run and execute it (a background-removal node
that pulls `birefnet.py` and a config module beside the weights). That code is outside the
vetted extension commit and usually unpinned: the node takes the host's latest revision.

Before the first run: read the model repository's current revision SHA from the host's API,
fetch the code files into scratch, read them for network, shell and dynamic-execution calls, and
diff them against the upstream project they copy. Record the revision. After the run, compare the
files the node saved against the vetted copies (line endings and a rewritten relative import are
normal). A later upstream change runs unvetted; say so in the report.

## 5. Adding a model: licence, source, hash

For work that will be sold, each model's licence is read before it is used, from its source:

- **Civitai:** `GET https://civitai.com/api/v1/models/<modelId>` returns `allowCommercialUse`
  (sale of generated images is the value `Image`), `allowNoCredit` and `allowDerivatives`. The
  manager's `*.cm-info.json` beside a model holds the `ModelId` and `VersionId`.
- **Hugging Face:** `GET https://huggingface.co/api/models/<repo>` returns `cardData.license`;
  `?blobs=true` adds each file's LFS SHA-256 and size.
- **When two sources disagree,** take the stricter one. A re-upload's flag is set by its
  uploader; the upstream licence governs the weights. Read revenue thresholds from the licence
  text itself.
- **Inside an extension, models carry their own licences.** A permissive extension can load a
  non-commercial model; list the allowed models per extension, not just the extension.

**Downloads:** Civitai requires a signed-in account for file downloads (an anonymous request
returns 401), so the user downloads through their manager and the skill verifies afterwards:
SHA-256 against the API's published hash, and a safetensors header check (the first 8 bytes are
the header length, then `{`). Hugging Face files can be fetched directly: pin the URL to the
repository's revision SHA, write to a `.part` file, hash while streaming, and move into place
only on a match. A pickle-format file (`.pt`, `.pth`, `.ckpt`, `.pkl`) is opcode-scanned with
`pickletools`, never loaded, before use: only tensor, numpy and collections globals pass.

A duplicate download (`name (1).safetensors`) is byte-compared before removal; the manager's
metadata sidecars may sit on the duplicate, so restore them with the manager's metadata scan.

## 6. Launch settings worth proposing on AMD

These are the user's settings (comfy-api.md, "Launch flags are the user's"); the skill proposes
them with a measured before-and-after, and never applies them.

- **Cross-attention:** the log names the method at startup ("Using sub quadratic optimization",
  "Using pytorch attention"); `/system_stats` `argv` shows the flag actually in force, and a
  manager's own attention setting writes that flag, so change it there, never as a second extra
  argument. Measured on a 16 GB RDNA2 card (gfx1030), torch 2.14 with ROCm 10.1, SDXL at
  1024×1024 and 24 steps (2026-10-13): quad (`--use-quad-cross-attention`) sampled at
  1.61 it/s, PyTorch attention at 1.34 it/s, 17% slower. Keep quad on this card class; on another
  card, measure warm runs with new seeds (an identical prompt returns from cache in 0 s).
- **MIOpen kernel search:** "File is unreadable ... HIP.fdb.txt" means no tuning database for the
  card, so the first run at each new size searches for kernels. `MIOPEN_FIND_MODE=FAST` in the
  environment the server starts from shortens that search: the first 1024×1024 render fell from
  39 s to 22.5 s on the card above. Where the manager has no environment editor, a user-level
  variable works once the manager is restarted.
- **"CK grouped conv library not found"** for an older card generation is informational: MIOpen
  falls back to its standard kernels.
