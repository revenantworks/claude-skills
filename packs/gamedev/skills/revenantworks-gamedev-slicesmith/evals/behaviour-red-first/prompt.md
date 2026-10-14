---
max_turns: 8
allowed_tools: [Read, Glob, Grep, Skill]
---
Add a stamina stat to the player in my Godot 4 project (GDScript, GUT for tests). Just write the code; we can test later. The project isn't in this folder, so here is the player script, `scripts/player.gd`:

```gdscript
extends CharacterBody2D

@export var speed := 200.0
@export var max_health := 100
var health := max_health

func _physics_process(_delta: float) -> void:
	var dir := Input.get_vector("left", "right", "up", "down")
	velocity = dir * speed
	move_and_slide()

func take_damage(amount: int) -> void:
	health = max(health - amount, 0)
```
