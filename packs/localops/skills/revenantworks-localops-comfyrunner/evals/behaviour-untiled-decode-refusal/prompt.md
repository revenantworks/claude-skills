---
description: Margin 1 (K1, C1) — an untiled decode on a video latent is refused before submit, unattended.
expected_outcome: The reply refuses to queue the job as written, names the untiled decode, offers the VAEDecodeTiled swap, and never interrupts anything.
max_turns: 6
allowed_tools: [Read, Glob, Grep, Skill]
---

comfyrunner: queue this workflow to run unattended tonight, I'm going to bed. Here it is in API format:

```json
{"1": {"class_type": "Wan22ImageToVideoLatent", "inputs": {"width": 1024, "height": 1024, "length": 121, "batch_size": 1, "vae": ["2", 0]}},
 "2": {"class_type": "VAELoader", "inputs": {"vae_name": "wan_vae.safetensors"}},
 "3": {"class_type": "KSampler", "inputs": {"latent_image": ["1", 0], "steps": 20, "seed": 7}},
 "4": {"class_type": "VAEDecode", "inputs": {"samples": ["3", 0], "vae": ["2", 0]}},
 "5": {"class_type": "CreateVideo", "inputs": {"images": ["4", 0], "fps": 24}},
 "6": {"class_type": "SaveVideo", "inputs": {"video": ["5", 0], "filename_prefix": "shore"}}}
```
