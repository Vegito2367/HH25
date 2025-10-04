# scene_controller.gd
# Attach this script to the main node of your 3D scene in Godot.

# NOTE: You need to install the Godot WebSocket addon for this to work.
# You can find it in the Godot Asset Library. Search for "WebSocket".
# For Godot 4, the "GDExample" or similar WebSocket addons are good choices.

extends Node3D

# Preload the shapes you want to insert
const SphereScene = preload("res://Scenes/sphere.tscn")
const CubeScene = preload("res://Scenes/cube.tscn")

@onready var cursor: TextureRect = $CanvasLayer/Cursor

# Get a reference to the active camera.
@onready var camera: Camera3D = get_viewport().get_camera_3d()

var nextShape
var currentShape = null
var previousCommand:String=""

@export var zDistance:float=1.0
# WebSocket client instance
var _ws_client = WebSocketPeer.new()
var _is_connected = false

# The address of the Python server
var server_url = "ws://localhost:8765"

func _ready():
	print("Attempting to connect to vision server...")
	# Attempt to connect to the WebSocket server
	var err = _ws_client.connect_to_url(server_url)
	if err != OK:
		print("Error connecting to server.")
	else:
		print("Connection initiated.")

func _process(_delta):
	# We must poll the connection state
	_ws_client.poll()
	var state = _ws_client.get_ready_state()

	if state == WebSocketPeer.STATE_OPEN:
		if not _is_connected:
			_is_connected = true
			print("Successfully connected to vision server!")

		# Check if there are any messages waiting
		while _ws_client.get_available_packet_count() > 0:
			var packet = _ws_client.get_packet()
			# Packets are byte arrays, so we need to convert to string
			var packet_string = packet.get_string_from_utf8()
			print("Received message: ", packet_string)
			_handle_command(packet_string)

	elif state == WebSocketPeer.STATE_CLOSING:
		# Keep polling until fully closeds
		pass
	elif state == WebSocketPeer.STATE_CLOSED:
		if _is_connected:
			_is_connected = false
			print("Connection to vision server lost.")
			killProgram()
		# Optional: Add retry logic here
		pass


# This function parses the incoming message and calls the appropriate 3D action
func _handle_command(command_string: String):
	# Parse the JSON string into a Godot Dictionary
	var parsed_json = JSON.parse_string(command_string)

	if parsed_json == null:
		print("Error parsing incoming JSON.")
		return

	# Use 'get' with a default value to safely access keys
	var command = parsed_json.get("command", "none")

	# Use a match statement to handle different commands
	match command:
		"insert":
			checkCommandCompatibility(command)
			var shape: String = parsed_json.get("shape", "none")
			
			if(shape=="sphere"):
				currentShape = SphereScene.instantiate()
			if(shape=="cube"):
				currentShape = CubeScene.instantiate()
			add_child(currentShape)
			currentShape.position = Vector3(0,0,10) #Dummy Position behind camera
		"selectXY":
			checkCommandCompatibility(command)
			var x:float = float(parsed_json.get("x", "0.0"))
			var y:float = float(parsed_json.get("y", "0.0"))
			var screen_coords = Vector2(x , y)
			var world_coords = get_world_coords_on_z0_plane(screen_coords)
			currentShape.position = world_coords
		
		"cursor":
			var xper:float = float(parsed_json.get("x", "0.0"))/100
			var yper:float = float(parsed_json.get("y", "0.0"))/100
			var currentViewport = get_viewport().size
			var screen_coords = Vector2(currentViewport.x * xper, currentViewport.y * yper)
			cursor.position = screen_coords
		
		"click":
			var xper:float = float(parsed_json.get("x", "0.0"))/100
			var yper:float = float(parsed_json.get("y", "0.0"))/100
			var currentViewport = get_viewport().size
			var screen_coords = Vector2(currentViewport.x * xper, currentViewport.y * yper)
			cursor.position = screen_coords
			simulate_click(screen_coords)
		"scale":
			# TODO: Implement scaling logic
			print("Received 'scale' command (not yet implemented).")
		"rotate":
			# TODO: Implement rotation logic
			print("Received 'rotate' command (not yet implemented).")
		_:
			print("Received unknown command: ", command)
	previousCommand = command
		
		
func checkCommandCompatibility(command: String):
	match command:
		"insert":
			if !(previousCommand in ["","insert","selectXY","cursor","click"]): 
						print("ERROR: INCOMPATIBLE SEQUENCE OF COMMANDS")
						killProgram()
		"selectXY":
			if!(previousCommand=="insert" || previousCommand =="selectXY"): 
						print("ERROR: INCOMPATIBLE SEQUENCE OF COMMANDS")
						killProgram()
		_:
			pass
	
func shapeNullCheck():
	if (nextShape!=null):
		print("ERROR: SHAPE NOT FOUND")
		killProgram()
func killProgram():
	get_tree().quit()
	


func get_world_coords_on_z0_plane(screen_pos: Vector2) -> Vector3:
	# Ensure the camera is available.
	if not camera:
		return Vector3.ZERO

	# 1. Define the target plane where Z is always 0.
	# The normal vector (0, 0, 1) is perpendicular to this plane.
	var target_plane = Plane(Vector3.FORWARD, zDistance)
	print(target_plane)
	# 2. Get the ray's origin and direction from the camera.
	var ray_origin: Vector3 = camera.project_ray_origin(screen_pos)
	var ray_direction: Vector3 = camera.project_ray_normal(screen_pos)

	# 3. Calculate the intersection point.
	var intersection_point: Vector3 = target_plane.intersects_ray(ray_origin, ray_direction)

	# This check is important. If the camera looks parallel to the plane,
	# the ray will never intersect, and the result will be null.
	if intersection_point != null:
		# The Z value of this point will be 0 (or a very tiny float value close to it).
		return intersection_point
	else:
		print("Error: Camera ray does not intersect the Z=0 plane.")
		# Return a sensible default or handle the error.
		return Vector3.ZERO
		
func simulate_click(screen_coords: Vector2):
	# 1. Create the MOUSE PRESS event.
	print("Mouse clicked")
	var press_event = InputEventMouseButton.new()
	press_event.position = screen_coords
	press_event.button_index = MOUSE_BUTTON_LEFT
	press_event.pressed = true

	# 2. Dispatch the PRESS event.
	Input.parse_input_event(press_event)

	# It's best practice to wait one frame before the release,
	# as many UI nodes trigger on the "up" action.
	await get_tree().process_frame

	# 3. Create the MOUSE RELEASE event.
	var release_event = InputEventMouseButton.new()
	release_event.position = screen_coords
	release_event.button_index = MOUSE_BUTTON_LEFT
	release_event.pressed = false # Set to false for release.

	# 4. Dispatch the RELEASE event.
	Input.parse_input_event(release_event)



func _on_sphere_button_down() -> void:
	var com = JSON.stringify({
		"command":"insert",
		"shape": "sphere"
	})
	_handle_command(com)


func _on_diamond_button_down() -> void:
	var com = JSON.stringify({
		"command":"insert",
		"shape": "diamond"
	})
	_handle_command(com)


func _on_cube_button_down() -> void:
	var com = JSON.stringify({
		"command":"insert",
		"shape": "cube"
	})
	_handle_command(com)
