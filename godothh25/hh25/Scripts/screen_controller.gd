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
@onready var baseParent:Node3D = $Parent
# Get a reference to the active camera.
@onready var debugBox:TextEdit = $CanvasLayer/DebugBox
@onready var camera: Camera3D = get_viewport().get_camera_3d()
var targetPosition: Vector3
var targetBasis: Basis
var nextShape
var currentShape = null
var previousCommand:String=""
@export var lerpCoeff:float = 4.0
@export var slerpCoeff = 4.0
@export var zDistance:float=1.0
@export var zSpeed: float = 0.02
@export var rotateSpeed: float = 0.02
@export var moveSpeed: float = 0.02
var originalPosition:Vector3
# WebSocket client instance
var _ws_client = WebSocketPeer.new()
var _is_connected = false
# The address of the Python server
var server_url = "ws://localhost:8765"
@export var nodesList:Array[Node3D]
func _ready():
	print("Attempting to connect to vision server...")
	# Attempt to connect to the WebSocket server
	targetPosition = camera.position
	targetBasis = camera.global_transform.basis
	originalPosition = camera.global_position
	var err = _ws_client.connect_to_url(server_url)
	if err != OK:
		print("Error connecting to server.")
	else:
		print("Connection initiated.")

func _process(_delta):
	if(currentShape!=null):
		debugBox.text = currentShape.name
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
	
	camera.global_position = camera.global_position.lerp(targetPosition, lerpCoeff * _delta)
	baseParent.global_transform.basis = baseParent.global_transform.basis.slerp(targetBasis, slerpCoeff * _delta)


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
	print("COM RUN:",command)
	match command:
		"insert":
			if !checkCommandCompatibility(command):
				return
			var shape: String = parsed_json.get("shape", "none")
			if(currentShape!=null && previousCommand=="insert"):
				remove_child(currentShape)
			if(shape=="sphere"):
				currentShape = SphereScene.instantiate()
			if(shape=="cube"):
				currentShape = CubeScene.instantiate()
			
			if (previousCommand == "insert" && currentShape.position == Vector3(0,0,10)):
				return
			baseParent.add_child(currentShape)
			currentShape.global_position= Vector3(0,0,10)
			previousCommand = command
			 #Dummy Position behind camera
		"selectXY":
			if !checkCommandCompatibility(command):
				return
			var screen_coords = cursor.position
			var world_coords = get_world_coords_on_camera_plane(screen_coords)
			currentShape.global_position= world_coords
			previousCommand = command
		
		"selectZ":
			if !checkCommandCompatibility(command):
				return
			var z:float = float(parsed_json.get("z", "0.0"))
			pushObjectBack(z)
			nodesList.append(currentShape)
			currentShape=null
			previousCommand = command
		
		"cursor":
			debugBox.text="Cursor"
			var xper:float = float(parsed_json.get("x", "0.0"))/100
			var yper:float = float(parsed_json.get("y", "0.0"))/100
			var currentViewport = get_viewport().size
			var screen_coords = Vector2(currentViewport.x * xper, currentViewport.y * yper)
			cursor.position = screen_coords
			if(currentShape!=null && cursor.position.y>17):
				if(previousCommand=="insert"):
					currentShape.global_position = get_world_coords_on_camera_plane(screen_coords)
				elif (previousCommand=="selectXY"):
					var signZ=getSign(xper*100)
					print("SIGN:",signZ)
					pushObjectBack((signZ*-1*zSpeed))
		"select":
			if previousCommand=="insert":
				_handle_command(JSON.stringify({
					"command":"selectXY",
					"x": cursor.position.x,
					"y":cursor.position.y
				}))
				
			elif previousCommand=="selectXY":
				_handle_command(JSON.stringify({
					"command":"selectZ",
					"z": 0,
				}))
		"click":
			var xper:float = float(parsed_json.get("x", "0.0"))/100
			var yper:float = float(parsed_json.get("y", "0.0"))/100
			var currentViewport = get_viewport().size
			var screen_coords = Vector2(currentViewport.x * xper, currentViewport.y * yper)
			cursor.position = screen_coords
			simulate_click(screen_coords)
		"move":

			var mx: float = float(parsed_json.get("x",0.0))
			var my: float = float(parsed_json.get("y",0.0))
			var currentViewport = get_viewport().size
			var screen_coords = Vector2(currentViewport.x * mx, currentViewport.y * my) *0.01
			debugBox.text = str(screen_coords)
			cursor.position = screen_coords
			var mz: float = float(parsed_json.get("z",0.0))
			var xv = getSign(mx) * moveSpeed
			var yv = getSign(my) * moveSpeed
			var zv = 0 * moveSpeed
			var directionZ = -camera.global_transform.basis.z
			var directionY = -camera.global_transform.basis.y
			var directionX = camera.global_transform.basis.x
			targetPosition += directionY*yv + directionX*xv
		"stagerotate":
			var rx: float = float(parsed_json.get("x",0.0)) 
			var ry: float = float(parsed_json.get("y",0.0))
			var currentViewport = get_viewport().size
			var screen_coords = Vector2(currentViewport.x * rx, currentViewport.y * ry)
			cursor.position = screen_coords
			var signX=getSign(rx)
			var signY=getSign(ry)
			
			var current_roll = baseParent.global_transform.basis.get_euler()
			var target_euler = Vector3(current_roll.x+signX*rotateSpeed, current_roll.y + signY*rotateSpeed, current_roll.z)
			targetBasis = Basis.from_euler(target_euler)
		_:
			print("Received unknown command: ", command)
	
		
		
func checkCommandCompatibility(command: String):
	match command:
		"insert":
			if !(previousCommand in ["","insert","selectZ"]): 
				print("ERROR: INCOMPATIBLE SEQUENCE OF COMMANDS")
				return false
		"selectXY":
			if !(previousCommand in ["","insert","selectXY"]): 
				print("ERROR: INCOMPATIBLE SEQUENCE OF COMMANDS")
				return false
		"selectZ": 
			if!(previousCommand in ["selectXY", "selectZ"]): 
				print("ERROR: INCOMPATIBLE SEQUENCE OF COMMANDS")
				return false
		_:
			pass
	return true
	
	
func shapeNullCheck():
	if (nextShape!=null):
		print("ERROR: SHAPE NOT FOUND")
		killProgram()
func killProgram():
	get_tree().quit()

func getSign(val:float):
	if(val>75):
		return 1
	elif val<25:
		return -1
	else:
		return 0
func pushObjectBack(z:float):
	var prevpos = currentShape.global_position
	var zDirectionFromCamera = camera.global_transform.basis.z
	currentShape.global_position += (zDirectionFromCamera) * z

func get_world_coords_on_z0_plane(screen_pos: Vector2) -> Vector3:
	# Ensure the camera is available.
	if not camera:
		return Vector3.ZERO



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
		
func get_world_coords_on_camera_plane(screen_pos: Vector2) -> Vector3:
	if not camera:
		return Vector3.ZERO

	# 1. The plane's normal is the camera's forward direction.
	# The -Z axis is forward in Godot, making the plane's normal face the camera.
	var plane_normal: Vector3 = -camera.global_transform.basis.z

	# 2. Calculate a point on the plane.
	# Start at the camera's position and move `distance_from_camera` units forward.
	var point_on_plane: Vector3 = camera.global_position + (plane_normal * zDistance)

	# 3. Create the plane object.
	# The constructor takes the normal and the distance from the WORLD ORIGIN (d).
	# We can calculate 'd' using the dot product of the normal and a point on the plane.
	var d = plane_normal.dot(point_on_plane)
	var target_plane = Plane(plane_normal, d)

	# 4. Get the ray from the camera as before.
	var ray_origin: Vector3 = camera.project_ray_origin(screen_pos)
	var ray_direction: Vector3 = camera.project_ray_normal(screen_pos)

	# 5. Calculate the intersection point on our new dynamic plane.
	var intersection_point: Vector3 = target_plane.intersects_ray(ray_origin, ray_direction)

	if intersection_point != null:
		return intersection_point
	else:
		# This error is less likely now but still good practice to keep.
		print("Error: Camera ray does not intersect the plane.")
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
	print("SPHERE INSERTED click")
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
	print("CUBE INSERTED click")
	var com = JSON.stringify({
		"command":"insert",
		"shape": "cube"
	})
	_handle_command(com)
