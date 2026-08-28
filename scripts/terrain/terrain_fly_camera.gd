extends Camera3D

@export var move_speed := 420.0
@export var fast_multiplier := 5.0
@export var mouse_sensitivity := 0.0025

var looking := false


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_RIGHT:
		looking = event.pressed
		Input.set_mouse_mode(
			Input.MOUSE_MODE_CAPTURED if looking else Input.MOUSE_MODE_VISIBLE
		)

	if event is InputEventMouseMotion and looking:
		rotate_y(-event.relative.x * mouse_sensitivity)
		rotation.x = clamp(
			rotation.x - event.relative.y * mouse_sensitivity,
			deg_to_rad(-85.0),
			deg_to_rad(85.0)
		)

	if event.is_action_pressed("ui_cancel"):
		looking = false
		Input.set_mouse_mode(Input.MOUSE_MODE_VISIBLE)


func _process(delta: float) -> void:
	var input_vector := Vector3.ZERO
	if Input.is_key_pressed(KEY_W):
		input_vector.z -= 1.0
	if Input.is_key_pressed(KEY_S):
		input_vector.z += 1.0
	if Input.is_key_pressed(KEY_A):
		input_vector.x -= 1.0
	if Input.is_key_pressed(KEY_D):
		input_vector.x += 1.0
	if Input.is_key_pressed(KEY_E):
		input_vector.y += 1.0
	if Input.is_key_pressed(KEY_Q):
		input_vector.y -= 1.0

	if input_vector.is_zero_approx():
		return

	var speed := move_speed
	if Input.is_key_pressed(KEY_SHIFT):
		speed *= fast_multiplier

	var horizontal := global_transform.basis * Vector3(
		input_vector.x,
		0.0,
		input_vector.z
	)
	var vertical := Vector3.UP * input_vector.y
	global_position += (
		(horizontal + vertical).normalized() * speed * delta
	)
