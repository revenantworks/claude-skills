---
description: Margin M1 (test case T2) — a GPU run whose log lacks the device line is FAILED-GPU, never a pass.
expected_outcome: The reply says FAILED-GPU and does not file the transcript as a good GPU run.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

I ran whisper on the GPU overnight for interview.wav (52 minutes). The transcript came out and looks fine. Here are the log lines that mention the backend:

```
whisper_init_with_params_no_state: use gpu    = 1
whisper_backend_init_gpu: no GPU found
whisper_model_load:          CPU total size =  1623.92 MB
whisper_print_timings:    total time = 2934120.55 ms
```

Did the GPU do the work, and can I mark this run as passed and file the transcript?
