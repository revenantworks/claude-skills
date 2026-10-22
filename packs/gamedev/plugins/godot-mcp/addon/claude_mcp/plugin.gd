@tool
extends EditorPlugin
## Claude MCP, the editor half of the godot-mcp plugin.
##
## Listens on 127.0.0.1 only and answers one JSON request per line. Every request carries the
## per-session token this plugin writes, with the port, to res://.godot/claude_mcp/session.json
## (Godot's cache folder, which git ignores). The command list below is fixed: nothing here
## deletes a node or a file, runs code sent over the socket, or saves anywhere but the open
## scene's own file. Editor Settings > claude_mcp/read_only refuses every edit command.

const PROTOCOL := 1
const PORT := 6010                     # first port tried; the next 9 are fallbacks
const SESSION_FILE := "res://.godot/claude_mcp/session.json"
const MAX_LINE := 1 << 20              # largest request line, after the token is accepted
const MAX_FIRST_LINE := 8192           # largest line before it (the token check)
const READ_ONLY_SETTING := "claude_mcp/read_only"
const WRITE_COMMANDS := ["add_node", "set_property", "save_scene"]

var _server := TCPServer.new()
var _peer: StreamPeerTCP               # one client at a time; others wait in the backlog
var _buf := PackedByteArray()
var _authed := false
var _token := ""                       # the lock: every request must carry it
var _port := 0
var _capture := _Capture.new()         # keeps the editor's recent messages
var _last_run_started := 0.0           # when Claude last pressed Play (unix seconds)


# Runs when the plugin is ticked on (or the editor opens with it on).
func _enter_tree() -> void:
	var es := EditorInterface.get_editor_settings()
	if not es.has_setting(READ_ONLY_SETTING):
		es.set_setting(READ_ONLY_SETTING, false)
	es.add_property_info({"name": READ_ONLY_SETTING, "type": TYPE_BOOL})
	_token = Crypto.new().generate_random_bytes(16).hex_encode()
	var base := PORT
	if OS.has_environment("GODOT_MCP_PORT"):
		base = OS.get_environment("GODOT_MCP_PORT").to_int()
	for p in range(base, base + 10):
		if _server.listen(p, "127.0.0.1") == OK:   # 127.0.0.1 = this PC only
			_port = p
			break
	if _port == 0:
		push_warning("Claude MCP: no free port in %d-%d" % [base, base + 9])
		return
	OS.add_logger(_capture)
	_write_session()
	print("Claude MCP: listening on 127.0.0.1:%d%s" % [_port, " (read-only)" if _read_only() else ""])


# Runs when the plugin is ticked off or the editor closes. Leaves nothing behind.
func _exit_tree() -> void:
	_drop()
	_server.stop()
	OS.remove_logger(_capture)
	DirAccess.remove_absolute(ProjectSettings.globalize_path(SESSION_FILE))


func _write_session() -> void:
	var path := ProjectSettings.globalize_path(SESSION_FILE)
	DirAccess.make_dir_recursive_absolute(path.get_base_dir())
	var f := FileAccess.open(path, FileAccess.WRITE)
	f.store_string(JSON.stringify({"protocol": PROTOCOL, "port": _port, "token": _token}))


func _read_only() -> bool:
	return bool(EditorInterface.get_editor_settings().get_setting(READ_ONLY_SETTING))


func _drop() -> void:
	if _peer:
		_peer.disconnect_from_host()
	_peer = null
	_buf = PackedByteArray()
	_authed = false


# Runs every editor frame: take the next client when free, read finished lines, answer them.
func _process(_delta: float) -> void:
	if _port == 0:
		return
	if _peer == null and _server.is_connection_available():
		_peer = _server.take_connection()
	if _peer == null:
		return
	_peer.poll()
	if _peer.get_status() != StreamPeerTCP.STATUS_CONNECTED:
		_drop()
		return
	if _peer.get_available_bytes() > 0:
		_buf.append_array(_peer.get_data(_peer.get_available_bytes())[1])
	var nl := _buf.find(10)                  # 10 = the newline byte
	while nl >= 0 and _peer:
		var line := _buf.slice(0, nl).get_string_from_utf8()
		_buf = _buf.slice(nl + 1)
		var reply := _handle(line)
		_peer.put_data((JSON.stringify(reply) + "\n").to_utf8_buffer())
		if reply.get("error_code") == "BAD_TOKEN":
			_drop()                          # a wrong token ends the connection
			return
		nl = _buf.find(10)
	if _buf.size() > (MAX_LINE if _authed else MAX_FIRST_LINE):
		_drop()                              # an oversized line is not a request


# Compares every byte, so the time taken does not hint at how much of a guess was right.
func _same(a: String, b: String) -> bool:
	var x := a.to_utf8_buffer()
	var y := b.to_utf8_buffer()
	var diff := x.size() ^ y.size()
	for i in mini(x.size(), y.size()):
		diff |= x[i] ^ y[i]
	return diff == 0


# One request in, one reply out. A fixed list of commands is the safety rule.
func _handle(line: String) -> Dictionary:
	var req = JSON.parse_string(line)
	if typeof(req) != TYPE_DICTIONARY:
		return {"ok": false, "error_code": "BAD_REQUEST", "error": "not a JSON object"}
	if not _same(str(req.get("token", "")), _token):
		return {"ok": false, "error_code": "BAD_TOKEN", "error": "bad token"}
	_authed = true
	var args = req.get("args", {})
	if typeof(args) != TYPE_DICTIONARY:
		return {"ok": false, "error_code": "BAD_REQUEST", "error": "args must be an object"}
	var cmd := str(req.get("cmd", ""))
	if cmd in WRITE_COMMANDS and _read_only():
		return {"ok": false, "error_code": "READ_ONLY",
			"error": "read-only: Editor Settings > claude_mcp/read_only is on"}
	var result
	match cmd:
		"status": result = _cmd_status()
		"run_scene": result = _cmd_run_scene(args)
		"stop_scene": result = _cmd_stop_scene()
		"editor_log": result = _cmd_editor_log(args)
		"scene_tree": result = _cmd_scene_tree(args)
		"add_node": result = _cmd_add_node(args)
		"set_property": result = _cmd_set_property(args)
		"save_scene": result = _cmd_save_scene()
		_: result = "unknown command"
	if typeof(result) == TYPE_STRING:      # a handler returns a String when it refuses
		return {"ok": false, "error_code": "REFUSED", "error": result}
	return {"ok": true, "result": result}


# Helpers are named _cmd_*: EditorPlugin has built-in methods like _run_scene, and a helper with
# the same name would break the whole script.
func _cmd_status() -> Dictionary:
	var root := EditorInterface.get_edited_scene_root()
	return {
		"godot": Engine.get_version_info().string,
		"project": ProjectSettings.get_setting("application/config/name"),
		"main_scene": ProjectSettings.get_setting("application/run/main_scene"),
		"edited_scene": root.scene_file_path if root else "",
		"playing": EditorInterface.is_playing_scene(),
		"game_log": _game_log_path(),
		"last_run_started": _last_run_started,   # 0 = no run since the plugin loaded
		"read_only": _read_only(),
	}


# --- run a scene, stop it, read output -----------------------------------------------------

# The game runs as its own process, so the editor cannot see its prints. But Godot writes
# them to a log file (on by default on PC); the Python server reads that file.
#
# The game's user:// folder is worked out here, not with globalize_path: inside the editor,
# user:// can point at the default folder even when the project (or an override.cfg, as in
# Evolution's worktrees) gives the game a custom one, and then we would read the wrong log.
func _game_log_path() -> String:
	var p := str(ProjectSettings.get_setting("debug/file_logging/log_path", "user://logs/godot.log"))
	if not p.begins_with("user://"):
		return ProjectSettings.globalize_path(p)
	var app := str(ProjectSettings.get_setting("application/config/name", "")).validate_filename()
	var use_custom: bool = ProjectSettings.get_setting("application/config/use_custom_user_dir", false)
	var custom := str(ProjectSettings.get_setting("application/config/custom_user_dir_name", ""))
	# The editor never applies override.cfg to its own settings (tested), but the game does, so
	# read it here: Evolution's worktrees set their user folder there.
	var ov := ConfigFile.new()
	if ov.load("res://override.cfg") == OK:
		use_custom = ov.get_value("application", "config/use_custom_user_dir", use_custom)
		custom = str(ov.get_value("application", "config/custom_user_dir_name", custom))
	var dir := OS.get_data_dir().path_join("Godot/app_userdata").path_join(app)
	if use_custom:
		dir = OS.get_data_dir().path_join(custom if custom != "" else app)
	return dir.path_join(p.trim_prefix("user://"))


# scene: "main", "current", or a res:// .tscn path. These are the editor's Play buttons.
func _cmd_run_scene(args: Dictionary):
	var scene := str(args.get("scene", "main"))
	if scene == "main":
		EditorInterface.play_main_scene()
	elif scene == "current":
		if EditorInterface.get_edited_scene_root() == null:
			return "no scene is open in the editor"
		EditorInterface.play_current_scene()
	elif scene.begins_with("res://") and (scene.ends_with(".tscn") or scene.ends_with(".scn")) \
			and not ".." in scene and not "\\" in scene \
			and ResourceLoader.exists(scene):
		EditorInterface.play_custom_scene(scene)
	else:
		return "scene must be main, current, or an existing res:// .tscn or .scn path"
	_last_run_started = Time.get_unix_time_from_system()
	return {"started": scene, "log_seq": _capture.last(), "game_log": _game_log_path()}


func _cmd_stop_scene() -> Dictionary:
	var was := EditorInterface.is_playing_scene()
	EditorInterface.stop_playing_scene()
	return {"was_playing": was}


# The editor's own messages and errors (script errors, warnings), newer than `since`.
func _cmd_editor_log(args: Dictionary) -> Dictionary:
	return _capture.since(int(args.get("since", 0)), bool(args.get("errors_only", false)),
		clampi(int(args.get("limit", 200)), 1, 1000))


# --- read and edit the open scene ----------------------------------------------------------
# Every edit goes through the editor's undo history, so Ctrl+Z reverses what Claude did.
# Nothing here deletes a node, sets a script, or saves anywhere but the scene's own file.

const BLOCKED := ["script", "owner", "scene_file_path"]   # setting a script = running code


func _cmd_scene_tree(args: Dictionary):
	var root := EditorInterface.get_edited_scene_root()
	if root == null:
		return "no scene is open in the editor"
	return {"scene": root.scene_file_path,
		"tree": _describe(root, root, 0, clampi(int(args.get("max_depth", 6)), 0, 32))}


func _describe(node: Node, root: Node, depth: int, max_depth: int) -> Dictionary:
	var d := {"name": str(node.name), "type": node.get_class(), "path": str(root.get_path_to(node))}
	if node.get_script():
		d["script"] = node.get_script().resource_path
	var kids: Array[Dictionary] = []
	for c in node.get_children():
		if c.owner == root:                      # skip nodes inside instanced sub-scenes
			if depth < max_depth:
				kids.append(_describe(c, root, depth + 1, max_depth))
			else:
				d["children_hidden"] = true
	if kids.size() > 0:
		d["children"] = kids
	return d


func _find(path: String):
	var root := EditorInterface.get_edited_scene_root()
	if root == null:
		return "no scene is open in the editor"
	var node := root if path in ["", "."] else root.get_node_or_null(NodePath(path))
	return node if node else "no node at '%s'" % path


# value: a JSON value; value_godot: Godot's text form, e.g. "Vector2(10, 20)". str_to_var never
# builds an object, so no code can sneak in through a value.
func _coerce(node: Node, prop: String, args: Dictionary):
	if prop in BLOCKED:
		return "property '%s' cannot be set through Claude MCP" % prop
	var info := {}
	for p in node.get_property_list():
		if p.name == prop and p.usage & PROPERTY_USAGE_EDITOR:
			info = p
	if info.is_empty():
		return "%s has no editable property '%s'" % [node.get_class(), prop]
	if not args.has("value") and not args.has("value_godot"):
		return "give value (JSON) or value_godot (Godot text form)"
	var v = str_to_var(str(args.value_godot)) if args.has("value_godot") else args.get("value")
	if typeof(v) == TYPE_OBJECT:
		return "object values are not allowed"
	if info.type != TYPE_NIL and typeof(v) != info.type:
		var c = type_convert(v, info.type)
		if typeof(c) != info.type:
			return "'%s' wants a %s" % [prop, type_string(info.type)]
		v = c
	return [v]


func _cmd_add_node(args: Dictionary):
	var parent = _find(str(args.get("parent", ".")))
	if parent is String:
		return parent
	var type := str(args.get("type", ""))
	if not ClassDB.class_exists(type) or not ClassDB.is_parent_class(type, "Node") \
			or not ClassDB.can_instantiate(type) or type.begins_with("Editor"):
		return "'%s' is not a built-in Node class Claude may add" % type
	var node: Node = ClassDB.instantiate(type)
	if str(args.get("name", "")) != "":
		node.name = str(args.name).validate_node_name()
	var props = args.get("properties", {})
	for k in (props if props is Dictionary else {}):
		var r = _coerce(node, str(k), {"value": props[k]})
		if r is String:
			node.free()
			return r
		node.set(str(k), r[0])
	var root := EditorInterface.get_edited_scene_root()
	var ur := get_undo_redo()
	ur.create_action("Claude MCP: add %s" % type, UndoRedo.MERGE_DISABLE, root)
	ur.add_do_method(parent, "add_child", node, true)
	ur.add_do_method(node, "set_owner", root)    # owner = saved with the scene
	ur.add_do_reference(node)
	ur.add_undo_method(parent, "remove_child", node)
	ur.commit_action()
	return {"path": str(root.get_path_to(node)), "type": type, "saved": false}


func _cmd_set_property(args: Dictionary):
	var node = _find(str(args.get("path", ".")))
	if node is String:
		return node
	var prop := str(args.get("property", ""))
	var r = _coerce(node, prop, args)
	if r is String:
		return r
	var old = node.get(prop)
	var ur := get_undo_redo()
	ur.create_action("Claude MCP: set %s" % prop, UndoRedo.MERGE_DISABLE, node)
	ur.add_do_property(node, prop, r[0])
	ur.add_undo_property(node, prop, old)
	ur.commit_action()
	return {"property": prop, "old": var_to_str(old), "new": var_to_str(node.get(prop)), "saved": false}


func _cmd_save_scene():
	var root := EditorInterface.get_edited_scene_root()
	if root == null or root.scene_file_path == "":
		return "no saved scene is open (save a new scene once by hand first)"
	var err := EditorInterface.save_scene()
	return {"saved": root.scene_file_path} if err == OK else "save failed: %s" % error_string(err)


# A Logger (Godot 4.5+) sees every message and error the editor prints. It keeps the last
# 1,000. Loggers can be called from other threads, hence the mutex. Never print in here:
# printing calls the logger again.
class _Capture extends Logger:
	var _lock := Mutex.new()
	var _entries: Array[Dictionary] = []
	var _seq := 0
	# Strips terminal colour codes: Godot's JSON leaves them raw and Python refuses them.
	# PCRE escapes (\\x1b), not GDScript ones: "\u0000" would cut the pattern short.
	var _codes := RegEx.create_from_string("\\x1b\\[[0-9;?]*[A-Za-z]|[\\x00-\\x08\\x0b-\\x1f]")

	func _push(kind: String, text: String) -> void:
		_lock.lock()
		_seq += 1
		_entries.append({"seq": _seq, "kind": kind,
			"text": _codes.sub(text, "", true).strip_edges(false, true)})
		if _entries.size() > 1000:
			_entries.pop_front()
		_lock.unlock()

	func _log_message(message: String, error: bool) -> void:
		_push("error" if error else "message", message)

	func _log_error(function: String, file: String, line: int, code: String, rationale: String,
			_editor_notify: bool, error_type: int, _script_backtraces: Array[ScriptBacktrace]) -> void:
		var what := rationale if rationale != "" else code
		_push("warning" if error_type == ERROR_TYPE_WARNING else "error",
			"%s (%s:%d, %s)" % [what, file, line, function])

	func last() -> int:
		_lock.lock()
		var n := _seq
		_lock.unlock()
		return n

	func since(seq: int, errors_only: bool, limit: int) -> Dictionary:
		_lock.lock()
		var out: Array[Dictionary] = []
		for e in _entries:
			if e.seq > seq and (not errors_only or e.kind != "message"):
				out.append(e)
		_lock.unlock()
		return {"entries": out.slice(maxi(0, out.size() - limit))}
