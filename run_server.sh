#!/bin/bash

echo "🚀 Launching Python and Godot in separate tabs..."

# Get the absolute paths for the files we need.
SCRIPT_DIR=$(pwd)
VENV_PATH="${SCRIPT_DIR}/venv/bin/activate"
PYTHON_SCRIPT_PATH="${SCRIPT_DIR}/testvision.py"
GODOT_SCENE_PATH="Scenes/main.tscn"


osascript <<EOF
tell application "iTerm2"
    tell current window
        
        -- Create the first tab for the Python script
        create tab with default profile
        tell current session
            -- Let AppleScript safely build the command using 'quoted form of'
            write text "source " & (quoted form of "${VENV_PATH}") & "; python " & (quoted form of "${PYTHON_SCRIPT_PATH}")
        end tell
        
        -- Create the second tab for Godot
        create tab with default profile
        tell current session
            -- Use 'quoted form of' again for the Godot path
            write text "cd ~/Desktop/SideProjects/hackHarvard25/godothh25/hh25"
            write text "godot " & (quoted form of "${GODOT_SCENE_PATH}")
        end tell

    end tell
end tell
EOF