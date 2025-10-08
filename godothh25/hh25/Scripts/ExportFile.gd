extends Control

@onready var file_dialog = $FileDialog
@export var node_to_export: Node3D
@export var scene_node: Node3D

# --- Pausing Logic (Step 2) ---

# This function is called when the "SaveButton" is pressed.


# This function is called when the user successfully selects a file.
func _on_file_dialog_file_selected(path: String):
	# The game is still paused here.
	export_node_to_glb(node_to_export, path)
	# NOTE: The unpause is handled by popup_hide, which always fires after this.

# This function is called when the dialog closes, either by
# saving, canceling, or pressing the 'X' button.
	

# --- Function to call on success (Step 3) ---

func func2():
	scene_node.RESET()
	get_tree().paused = false
	
	# Add whatever logic you need here.

# --- Export Logic (Unchanged) ---

func export_node_to_glb(node: Node3D, file_path: String):
	var gltf_doc = GLTFDocument.new()
	var gltf_state = GLTFState.new()
	
	var error = gltf_doc.append_from_scene(node, gltf_state)
	if error != OK:
		print("Error appending node to GLTF document.")
		# If there's an error, we don't call func2.
		return

	error = gltf_doc.write_to_filesystem(gltf_state, file_path)
	if error != OK:
		print("Error writing GLB file to filesystem.")
		# Call your new function ONLY on successful save.
	func2()


func _on_save_file_button_down() -> void:
	get_tree().paused = true
	file_dialog.current_dir = "/Users/alexandermcgreevy/Documents/GitHub/HH25/output"
	file_dialog.current_file = "MyNewModel.glb"
	file_dialog.popup_centered()


func _on_file_dialog_canceled() -> void:
	get_tree().paused = false
