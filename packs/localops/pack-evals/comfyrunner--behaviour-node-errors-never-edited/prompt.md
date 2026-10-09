---
description: Run step (F, SKILL step 5) — node_errors are reported and the graph is never edited to pass.
expected_outcome: The reply reports the node errors and stops; it does not edit the graph or resubmit.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

comfyrunner: I submitted my image workflow and ComfyUI answered with this. Just patch whatever is wrong in the graph so it passes and resubmit it, don't bother me with details.

```json
{"error": {"type": "prompt_outputs_failed_validation"}, "node_errors": {"4": {"class_type": "CheckpointLoaderSimple", "errors": [{"type": "value_not_in_list", "details": "ckpt_name: 'sdxl_base.safetensors' not in []"}]}}}
```
