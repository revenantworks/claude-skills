# Install walkthrough — owner-run, once

**The skill never installs anything.** This file is for the user, who runs each step by hand.
Claude may read a step aloud, explain it, and run the **Verify** command after the user says
the step is done. Each step has a rollback. Windows commands first; Linux notes at the end.

Package ids below were not re-checked on the day this file was written: before each install,
run `winget show <id>` and confirm the publisher. Steps 3 and 5 may need an administrator shell
(the installers ask for it themselves); every other step runs as the normal user.

| # | Step | Command (owner runs) | Verify | Rollback |
|---|---|---|---|---|
| 1 | GPU driver exposes Vulkan | Update the GPU vendor's driver the usual way | after step 4: `vulkaninfo --summary` lists the card | the vendor's driver rollback |
| 2 | Git | `winget install --id Git.Git -e` | `git --version` | `winget uninstall --id Git.Git -e` |
| 3 | C++ build tools (admin) | `winget install --id Microsoft.VisualStudio.2022.BuildTools -e --override "--quiet --wait --add Microsoft.VisualStudio.Workload.VCTools --includeRecommended"` — use the current Build Tools id from `winget search BuildTools` | step 7's configure finds a compiler | `winget uninstall` the same id |
| 4 | CMake | `winget install --id Kitware.CMake -e` | `cmake --version` (new shell) | `winget uninstall --id Kitware.CMake -e` |
| 5 | Vulkan SDK | `winget install --id KhronosGroup.VulkanSDK -e` | new shell: `vulkaninfo --summary` lists the card; `echo $env:VULKAN_SDK` is set | `winget uninstall --id KhronosGroup.VulkanSDK -e` |
| 6 | FFmpeg | `winget install --id Gyan.FFmpeg -e` | `ffmpeg -version` | `winget uninstall --id Gyan.FFmpeg -e` |
| 7 | Clone and build at the pinned tag | in a tools folder of the user's choice: `git clone https://github.com/ggml-org/whisper.cpp; git -C whisper.cpp checkout <tag from engine.md>; cmake -S whisper.cpp -B whisper.cpp/build -DGGML_VULKAN=1; cmake --build whisper.cpp/build -j --config Release` | `whisper.cpp\build\bin\Release\whisper-cli.exe --help` prints the usage | delete the `whisper.cpp` folder |
| 8 | Models (owner's download) | `whisper.cpp\models\download-ggml-model.cmd large-v3-turbo`, then `… large-v3-turbo-q5_0` for the CPU path; optional VAD: `whisper.cpp\models\download-vad-model.cmd silero-v6.2.0` | the `.bin` files exist under `whisper.cpp\models\` | delete the `.bin` files |
| 9 | Record the binary | `Get-FileHash whisper.cpp\build\bin\Release\whisper-cli.exe -Algorithm SHA256` | a 64-character hash | — |
| 10 | Write the config | see below | `python scripts/whisper_run.py status` shows `config_present: true` | delete `whisperrunner.json` |
| 11 | First measurement | `python scripts/whisper_run.py audit <a 30-60 s clip>` | `gpu.backend.verdict` is `GPU-OK`; both `realtime_x` values present | — |

**Step 10, the config** — one PowerShell command, run from the folder that holds `whisper.cpp`
(it fills in full paths and the hash itself, and writes nothing else):

```powershell
$w = (Resolve-Path whisper.cpp).Path; $d = Join-Path $env:LOCALAPPDATA 'localops'; New-Item -ItemType Directory -Force $d | Out-Null; $bin = Join-Path $w 'build\bin\Release\whisper-cli.exe'; [ordered]@{ bin = $bin; model_gpu = (Join-Path $w 'models\ggml-large-v3-turbo.bin'); model_cpu = (Join-Path $w 'models\ggml-large-v3-turbo-q5_0.bin'); vad_model = (Join-Path $w 'models\ggml-silero-v6.2.0.bin'); sha256 = (Get-FileHash $bin -Algorithm SHA256).Hash.ToLower(); source = "built from source, tag <tag>, $(Get-Date -Format yyyy-MM-dd)" } | ConvertTo-Json | Set-Content -Encoding utf8 (Join-Path $d 'whisperrunner.json')
```

Drop the `vad_model` entry if step 8's VAD download was skipped.

**If step 11 reads FAILED-GPU:** the build likely missed Vulkan. Check that step 7's configure
output mentions Vulkan, that `VULKAN_SDK` was set in the shell that built it, and rebuild in a
fresh `build` folder. A dual-GPU machine may enumerate the integrated GPU first (`audit` reports
the card name).

**Rebuilding later** (a new tag): repeat step 7 at the new tag, then steps 9-11. The old hash no
longer matches, so unattended runs refuse until the config's `sha256` is updated — by design.

**Linux:** the package manager supplies git, cmake, a C++ compiler, the Vulkan headers and
`glslc` (or the LunarG SDK), and ffmpeg; build with the same two cmake lines; the binary is
`build/bin/whisper-cli`; models download with the `.sh` scripts; the config lives in
`$XDG_STATE_HOME/localops/` or `~/.local/state/localops/`; hash with `sha256sum`.
