extends CharacterBody3D
class_name TerrainPlayerProbe

@export var terrain_path := NodePath("../UmbralTerrain10km")
@export var walk_speed := 5.0
@export var sprint_speed := 9.0
@export var mouse_sensitivity := 0.0025
@export_range(0.0, 89.0, 0.5) var max_slope_degrees := 45.0
@export var ground_clearance := 0.05

@onready var camera_yaw: Node3D = $CameraYaw
@onready var camera_pitch: Node3D = $CameraYaw/CameraPitch
@onready var player_camera: Camera3D = (
	$CameraYaw/CameraPitch/SpringArm3D/PlayerCamera
)

var terrain: Terrain3D
var control_enabled := true
var grounded_on_terrain := false


func _ready() -> void:
	set_control_enabled(player_camera.current)


func _unhandled_input(event: InputEvent) -> void:
	if not control_enabled or not player_camera.current:
		return

	if event is InputEventMouseMotion \
			and Input.mouse_mode == Input.MOUSE_MODE_CAPTURED:
		camera_yaw.rotate_y(-event.relative.x * mouse_sensitivity)
		camera_pitch.rotation.x = clamp(
			camera_pitch.rotation.x - event.relative.y * mouse_sensitivity,
			deg_to_rad(-65.0),
			deg_to_rad(45.0)
		)

	if event.is_action_pressed("ui_cancel"):
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)

	if event is InputEventMouseButton \
			and event.button_index == MOUSE_BUTTON_LEFT \
			and event.pressed:
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)


func _physics_process(delta: float) -> void:
	if not _resolve_terrain():
		return

	if not grounded_on_terrain:
		grounded_on_terrain = _place_on_terrain(global_position)
		if not grounded_on_terrain:
			return
		print(
			"Umbral: jugador de escala humana ubicado en %s."
			% global_position
		)

	if not control_enabled or not player_camera.current:
		return

	var movement_input := Vector2.ZERO
	if Input.is_key_pressed(KEY_W):
		movement_input.y += 1.0
	if Input.is_key_pressed(KEY_S):
		movement_input.y -= 1.0
	if Input.is_key_pressed(KEY_A):
		movement_input.x -= 1.0
	if Input.is_key_pressed(KEY_D):
		movement_input.x += 1.0

	if movement_input.is_zero_approx():
		_place_on_terrain(global_position)
		return

	var forward := -camera_yaw.global_transform.basis.z
	forward.y = 0.0
	forward = forward.normalized()
	var right := camera_yaw.global_transform.basis.x
	right.y = 0.0
	right = right.normalized()
	var direction := (
		right * movement_input.x + forward * movement_input.y
	).normalized()
	var speed := sprint_speed if Input.is_key_pressed(KEY_SHIFT) else walk_speed
	var step := direction * speed * delta
	var candidate := global_position + step

	if _place_on_terrain(candidate):
		return
	if _place_on_terrain(global_position + Vector3(step.x, 0.0, 0.0)):
		return
	_place_on_terrain(global_position + Vector3(0.0, 0.0, step.z))


func set_control_enabled(enabled: bool) -> void:
	control_enabled = enabled
	if enabled:
		Input.set_mouse_mode(Input.MOUSE_MODE_CAPTURED)
	else:
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)


func _resolve_terrain() -> bool:
	if is_instance_valid(terrain):
		return true
	terrain = get_node_or_null(terrain_path) as Terrain3D
	return is_instance_valid(terrain) and is_instance_valid(terrain.data)


func _place_on_terrain(target_position: Vector3) -> bool:
	var terrain_height := terrain.data.get_height(target_position)
	if is_nan(terrain_height):
		return false

	var terrain_normal := terrain.data.get_normal(
		Vector3(target_position.x, terrain_height, target_position.z)
	)
	if terrain_normal.length_squared() < 0.001:
		return false
	var minimum_up_dot := cos(deg_to_rad(max_slope_degrees))
	if terrain_normal.normalized().dot(Vector3.UP) < minimum_up_dot:
		return false

	global_position = Vector3(
		target_position.x,
		terrain_height + ground_clearance,
		target_position.z
	)
	return true
