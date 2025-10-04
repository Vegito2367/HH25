# scene_controller.gd
# Attach this script to the main node of your 3D scene in Godot.

# NOTE: You need to install the Godot WebSocket addon for this to work.
# You can find it in the Godot Asset Library. Search for "WebSocket".
# For Godot 4, the "GDExample" or similar WebSocket addons are good choices.

extends Node3D

# Preload the shapes you want to insert
const SphereScene = preload("res://Scenes/sphere.tscn")
const CubeScene = preload("res://Scenes/cube.tscn")

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
		# Keep polling until fully closed
		pass
	elif state == WebSocketPeer.STATE_CLOSED:
		if _is_connected:
			_is_connected = false
			print("Connection to vision server lost.")
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
			var shape = parsed_json.get("shape", "none")
			_insert_shape(shape)
		"scale":
			# TODO: Implement scaling logic
			print("Received 'scale' command (not yet implemented).")
		"rotate":
			# TODO: Implement rotation logic
			print("Received 'rotate' command (not yet implemented).")
		_:
			print("Received unknown command: ", command)


# This function instantiates a new shape in the scene
func _insert_shape(shape_name: String):
	var new_shape_instance = null
	match shape_name:
		"sphere":
			print("Inserting Sphere")
			new_shape_instance = SphereScene.instantiate()
		"cube":
			print("Inserting Cube")
			new_shape_instance = CubeScene.instantiate()
		_:
			print("Cannot insert unknown shape: ", shape_name)
			return

	if new_shape_instance:
		# Add the new shape as a child of this node
		add_child(new_shape_instance)
		# Position it randomly for demonstration
		new_shape_instance.position = Vector3(0,0,-1)
