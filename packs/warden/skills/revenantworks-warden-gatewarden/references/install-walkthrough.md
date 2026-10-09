# Install walkthrough — the gatewarden hooks, installed by the owner

**gatewarden installs nothing.** Every step below is the owner's to run, one at a time, with a
check after it and a way back. Commands are PowerShell on Windows; `<skill>` is this skill's folder
and `<home>` is your user folder (`$HOME`). Python 3 must be on PATH (`python --version`).

Pick the hooks you want. Each works alone; the push gate changes daily work the most (every push
then needs an intent and a CI stamp), so start with it in one repo.

## Contents

1 Copy the files · 2 Check each hook offline · 3 Build the finished settings file · 4 Install it ·
5 First use · 6 Roll back

## 1 · Copy the files

```powershell
New-Item -ItemType Directory -Force "$HOME\.claude\hooks\gatewarden" | Out-Null; Copy-Item "<skill>\scripts\hooks\*.py" "$HOME\.claude\hooks\gatewarden\"
```

- **Verify:** `Get-ChildItem "$HOME\.claude\hooks\gatewarden" -Name` lists ten files:
  `call_cap.py ci_stamp.py golive_block.py heredoc_guard.py hooklib.py hyperv_lock.py launch_throttle.py push_gate.py warden_digest.py warden_review.py`.
- **Rollback:** `Remove-Item -Recurse "$HOME\.claude\hooks\gatewarden"`.

**Pin hypervrunner's scripts** (only if you install `hyperv_lock`). The lock lets Claude run
hypervrunner's `teardown.py`, `cleanroom.py` and `vmctl.py` only while each matches the sha256 you
pin here. `<hypervrunner>` is that skill's folder.

```powershell
python "$HOME\.claude\hooks\gatewarden\hyperv_lock.py" --pin "<hypervrunner>\scripts"
```

- **Verify:** it prints three lines (`teardown.py`, `cleanroom.py`, `vmctl.py`, each with a 64-character
  hash), then `wrote ...\hyperv_lock.pins.json`.
- **Rollback:** `Remove-Item "$HOME\.claude\hooks\gatewarden\hyperv_lock.pins.json"` (Claude can then
  run none of the three scripts).
- **Re-pin after any hypervrunner update**, however small: every edit to one of the three scripts
  changes its sha256, and the lock then blocks it until you run this command again. Pin from the
  files on disk; never copy a hash from a document, a changelog or a test. A change that edits a
  pinned script — a release, a fix round, a one-line patch — says so in its report and its
  CHANGELOG line, because nothing else tells you the lock will now block it.

## 2 · Check each hook offline

Nothing is wired yet; these feed one sample event to each hook. Expected exit code after each.

```powershell
$h = "$HOME\.claude\hooks\gatewarden"
'{"tool_name":"PowerShell","tool_input":{"command":"Remove-VM -Name lab -Force"}}' | python "$h\hyperv_lock.py"; $LASTEXITCODE   # 2
'{"tool_name":"PowerShell","tool_input":{"command":"Get-VM"}}' | python "$h\hyperv_lock.py"; $LASTEXITCODE                      # 0
'{"tool_name":"PowerShell","tool_input":{"command":"python <hypervrunner>/scripts/teardown.py purge --due"}}' | python "$h\hyperv_lock.py"; $LASTEXITCODE    # 0 (pinned; use forward slashes)
'{"tool_name":"PowerShell","tool_input":{"command":"python x/revenantworks-localops-hypervrunner/scripts/teardown.py purge --due"}}' | python "$h\hyperv_lock.py"; $LASTEXITCODE    # 2 (no file there to match the pin)
'{"tool_name":"PowerShell","tool_input":{"command":"python x/revenantworks-localops-hypervrunner/scripts/teardown.py purge --entry aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"}}' | python "$h\hyperv_lock.py"; $LASTEXITCODE    # 2 (the owner's command)
'{"tool_name":"PowerShell","tool_input":{"command":"python x/revenantworks-localops-hypervrunner/scripts/teardown.py purge --entry aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee --due"}}' | python "$h\hyperv_lock.py"; $LASTEXITCODE    # 2 (--due does not carry --entry)
'{"tool_name":"PowerShell","tool_input":{"command":"pwsh -EncodedCommand UgBlAG0AbwB2AGUALQBWAE0AIABsAGEAYgA="}}' | python "$h\hyperv_lock.py"; $LASTEXITCODE    # 2 (decodes to Remove-VM lab)
'{"tool_name":"Bash","tool_input":{"command":"git status"},"cwd":"."}' | python "$h\push_gate.py"; $LASTEXITCODE              # 0
'{"tool_name":"Bash","tool_input":{"command":"bash -c \"git pu^sh origin main\""},"cwd":"."}' | python "$h\push_gate.py"; $LASTEXITCODE    # 0 (watch: logged, not blocked; 2 once push_gate is set to guard)
'{"tool_name":"Read","tool_input":{},"agent_id":"t1","agent_type":"none"}' | python "$h\call_cap.py"; $LASTEXITCODE           # 0
'{"tool_name":"Agent","tool_input":{}}' | python "$h\launch_throttle.py"; $LASTEXITCODE                                       # 0 (prints "not enforced" if no meter file)
'{"tool_name":"Bash","tool_input":{"command":"python send.py StartStream"}}' | python "$h\golive_block.py"; $LASTEXITCODE       # 2
'{"tool_name":"Bash","tool_input":{"command":"python obs_ws.py classify StartStream"}}' | python "$h\golive_block.py"; $LASTEXITCODE  # 0
'{"tool_name":"mcp__obs__start_stream","tool_input":{}}' | python "$h\golive_block.py"; $LASTEXITCODE                         # 2
```

- **Verify:** the exit codes match the comments. A different code means stop here.
- **Rollback:** none needed; nothing changed. `call_cap.py` wrote a count file under
  `$HOME\.claude\gatewarden\`; delete it if you like.

## 3 · Build the finished settings file

Back up the live file, then let `harden` write a finished copy beside it. It merges the hook entries
into what you already have and changes nothing else unless you add flags.

```powershell
Copy-Item "$HOME\.claude\settings.json" "$HOME\.claude\settings.json.bak-gatewarden"; python "<skill>\scripts\perm_audit.py" harden --settings "$HOME\.claude\settings.json" --add-hooks "$HOME/.claude/hooks/gatewarden" --hooks push_gate,hyperv_lock,heredoc_guard,call_cap,launch_throttle,golive_block
```

Drop names from `--hooks` to install fewer. On Windows `harden` also adds the PowerShell twin of each
Bash deny (it lists every change). `--add-hooks` also adds the deny rule `Edit(~/.claude/hooks/**)`,
so Claude's Write and Edit tools and shell redirections cannot rewrite a hook or the pin file (owner
HV2). A hooks folder elsewhere gets its own `Edit(<folder>/**)` rule as well.

- **Verify:** the output lists `added Edit(~/.claude/hooks/**)`, then `hook <name> on <matcher>` for
  each hook you chose, then `JSON parse: ok`, then exactly one `Copy-Item` line. Open
  `settings.hardened.json` and read it once.
- **Rollback:** `Remove-Item "$HOME\.claude\settings.hardened.json"`.

## 4 · Install it

Run the one `Copy-Item` line step 3 printed. It has this shape:

```powershell
Copy-Item -LiteralPath "<home>\.claude\settings.hardened.json" -Destination "<home>\.claude\settings.json"
```

- **Verify:** start a new Claude Code session and run `/hooks`; the entries show under PreToolUse.
  Ask Claude to run `Remove-VM -Name test-not-real`: it must be blocked by `hyperv lock`, whose
  reason names hypervrunner's `teardown.py` as the only way a VM is removed. Ask Claude to write a
  test line into `~/.claude/hooks/gatewarden/hyperv_lock.py`: the deny rule must refuse it.
- **Rollback:** `Copy-Item "$HOME\.claude\settings.json.bak-gatewarden" "$HOME\.claude\settings.json"`,
  then a new session.

## 5 · First use

- **Push gate, per repo:** Claude records the range the request named and runs the repo's CI
  through the stamp helper before pushing:
  `python "$HOME\.claude\hooks\gatewarden\push_gate.py" intend --repo . --max 3` and
  `python "$HOME\.claude\hooks\gatewarden\ci_stamp.py" run --repo . -- <the repo's CI command>`.
  Verify: a push with no intent runs in watch and adds a `push_gate.no_intent` line to
  `$HOME\.claude\gatewarden\events.jsonl`; a `--force` push is refused (hard rule).
- **Turning a rule up:** after a week, the session-start line names how many suggestions are waiting.
  `python "$HOME\.claude\hooks\gatewarden\warden_review.py"` prints them;
  `... warden_review.py set <rule> nudge` or `guard` applies one. Nothing promotes itself.
- **Call caps:** write `$HOME\.claude\gatewarden\call-caps.json` (the shape is in `hooks.md`).
  Verify: a subagent of a capped type gets the warning near its cap. With no file, the hook only counts.
  The hook also needs its `SubagentStop` entry (in the settings block) to log each subagent's end.
  Verify: after a subagent finishes, `$HOME\.claude\gatewarden\call-cap-events.jsonl` has an `end`
  line. After a block, `gatewarden capreview` reads that log.
- **Launch throttle:** needs a statusline that writes `$HOME\.claude\usage-windows.json`. Without it
  every launch passes with "not enforced". Verify by reading the note on the next launch.
- **Hyper-V lock, after every hypervrunner update:** re-pin, or the lock blocks the changed
  scripts with "does not match its pinned sha256". Run the pin command from step 1 again.
  Verify: ask Claude to run `python "<hypervrunner>\scripts\teardown.py" list`; it runs.
  Rollback: none needed; the old pins are replaced, and re-running the pin is the fix.
- **Go-live block:** nothing to configure. Verify: ask Claude to run
  `python -c "print('StartStream')"`; it must be blocked by `go-live block`. Ask it to read your OBS
  profile's `service.json`; that is blocked too. OBS itself is untouched by the check.

## 6 · Roll back everything

```powershell
Copy-Item "$HOME\.claude\settings.json.bak-gatewarden" "$HOME\.claude\settings.json"; Remove-Item -Recurse "$HOME\.claude\hooks\gatewarden", "$HOME\.claude\gatewarden"
```

Per-repo push files live under each repo's git folder (`.git\gatewarden\`) and do nothing without
the hook; delete them with the repo's other local state if you wish.
