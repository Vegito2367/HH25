# LookSmith

**Accessible 3D Modeling Through Facial Tracking**

---

## 🧠 Inspiration

LookSmith was created to open the world of 3D art to people who have the imagination but not the motor control to use traditional modeling software. Inspired by artists and creatives with disabilities who often face barriers in digital creation, our goal was to build a tool that allows anyone to shape 3D models — not with their hands, but with their expressions and movements.

## 💡 What It Does

LookSmith is an accessible facial-tracking 3D modeling platform built with Godot, Python, OpenCV, and MediaPipe. Users can sculpt and shape 3D objects using only their head and facial movements. The program translates subtle gestures, tracked in real-time, into precise modeling inputs, eliminating the need for a mouse, stylus, or keyboard.

A unique feature of LookSmith is its direct export integration. Users can instantly export their `.glb` models from the Godot application to our companion monetization site. This creates a seamless creative-to-commerce pipeline, allowing artists to showcase, share, or sell their creations, transforming a facial expression into a fully marketable 3D model.

## 🛠️ How We Built It

The system is comprised of a real-time vision engine communicating with a 3D modeling engine.

* **Engine**: The 3D modeling environment was built using Godot. Rather than exposing the full engine, we created a set of predefined commands which are hooked to specific facial gestures. A user can perform a gesture (such as tilting their head to the left or blinking three times) to initiate a command for a given shape. Commands are transferred from the Python vision engine to Godot using a sustained WebSocket connection, with data formatted as JSON to maximize information transmitted per query.

* **Tracking**: We built a real-time facial motion-capture system using MediaPipe. OpenCV is used for preprocessing tasks like video stabilization and temporal smoothing. This data is then streamed from the Python backend to the Godot frontend to control the cursor based on facial motions.

* **Modeling System**: We designed a custom mesh manipulation and gesture-mapping framework to translate facial data into 3D sculpting actions.

* **Export Pipeline**: An automated `.glb` exporter was built to package and upload models directly from the Godot application to the companion website.

* **Web Companion**: We developed a companion web platform for users to upload their models, create creator portfolios, and monetize their work.

* **Design Focus**: The project prioritized an accessibility-first UX, focusing on real-time feedback for intuitive, hands-free control.

## 🚧 Challenges We Ran Into

* **Motion Stability**: Filtering and smoothing noisy face-tracking data without introducing significant latency.
* **Gesture Mapping**: Designing natural, intuitive, and precise mappings between facial motions and complex modeling tools.
* **Performance**: Maintaining smooth, real-time rendering in Godot while simultaneously processing and streaming live tracking data.
* **Cross-Platform Assets**: Ensuring consistent `.glb` export quality and compatibility between the Godot application and the web platform.
* **Marketplace Integration**: Handling secure authentication, file uploads, and asset verification between the two distinct systems.

## 📚 What We Learned

* How to effectively integrate computer vision libraries with a real-time game engine for interactive applications.
* The importance of designing for accessibility and inclusivity from the initial stages of a project.
* The potential for accessibility-driven technology to unlock new career paths and opportunities in digital art.
* That merging art, empathy, and engineering can redefine what it means to create.

## 🌍 The Impact

LookSmith provides millions of people of determination the opportunity to interact with digital art in a new way. It empowers individuals with limited or no fine motor control to become digital artists for both recreational and entrepreneurial purposes. By enabling direct export to a monetized platform, it provides both creative freedom and a path to financial opportunity. We believe we are redefining digital art as something anyone can make, proving that innovation, accessibility, and creativity can exist hand in hand.