extends Node3D

# Import the necessary GLTF classes.
@onready var GLTFDocumentVar = preload("res://addons/gltf/gltf_document.gd")
@onready var GLTFStateVar = preload("res://addons/gltf/gltf_state.gd")

# We can trigger the export with a key press for testing.
func _unhandled_input(event):
	if event.is_action_pressed("ui_accept") or (event is InputEventKey and event.keycode == KEY_E and event.is_pressed()):
		print("Export key pressed. Starting GLB export...")
		
		# Define the output path. user:// is the standard place for saved files.
		var file_path = "user://my_model.glb"
		
		# Call the export function, passing 'self' as the node to export.
		export_node_to_glb(self, file_path)

# This function handles the actual export logic.
func export_node_to_glb(node_to_export: Node3D, file_path: String):
	var gltf_doc = GLTFDocument.new()
	var gltf_state = GLTFState.new()
	
	# Append this node (self) and its children to the GLTF document.
	var error = gltf_doc.append_from_node(node_to_export, gltf_state)
	if error != OK:
		print("Error appending node to GLTF document.")
		return

	# Write the result to a .glb file.
	error = gltf_doc.write_to_filesystem(gltf_state, file_path)
	if error != OK:
		print("Error writing GLB file to filesystem.")
	else:
		print("FILE EXPORTED")
