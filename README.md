# Twistopher-2-Single-Motor-Cube-Solver
### A single-motor Rubik's Cube-solving robot that never reorients the cube. Not built for speed or to break any records, but to simply see how absurdly complicated a solution can get when you add unnecessary (but creatively challenging) constraints.

**One motor. No cube reorientation. A completely unnecessary amount of mechanical complexity.**


**🔻Click the image below to watch Twistopher II autonomously scan and solve a scrambled Rubik's Cube.**

[![Watch Twistopher II Solving a Rubik's Cube](Image/image5.jpeg)](https://youtu.be/CT5pu-lk2kM)


---


## Overview

I'd wanted to build a Rubik's Cube-solving robot for quite a while, but by the time I had the tools and experience to attempt one, there were already countless designs online. I wanted to try something different.

The idea for Twistopher II came from rummaging through my electronics box and discovering that I had exactly one usable stepper motor. Rather than spending money on more motors, I wondered whether I could build an entire Rubik's Cube solver around just one.

After looking into existing single-motor designs, I found that they typically worked by reorienting the cube to present different faces to the same motor. So, naturally, I decided to make things even harder: **what if the cube couldn't be reoriented at all?**

After plenty of sketches, CAD iterations and abandoned ideas, I settled on a gearbox-like mechanism that allows a single stepper motor to selectively drive five of the cube's six faces. A servo moves the stepper between different gear engagements, while an arrangement of shafts, gears and bevel gears carries the rotation to each face. The sixth face remains fixed.

Of course, this technically involves two motors, but only **one motor actually rotates the cube's faces**. The servo simply selects where that motor's torque is delivered.

The finished machine is fully autonomous. Place a scrambled cube inside, press a button, and it scans the cube using a camera, reconstructs its state, calculates a solution using a five-face variant of Kociemba's two-phase algorithm, and executes the moves. Approximately 30 seconds later, you have a solved Rubik's Cube.

The project ended up being far more mechanically complicated than simply buying a few extra motors, which was rather the point. But it also became an opportunity to push my CAD, mechanical design, electronics and programming skills much further than I'd originally anticipated.

**Twistopher II isn't an attempt to build the fastest Rubik's Cube solver. It's an attempt to see how far an unnecessarily constrained idea can be taken — and actually make it work.**


## Design Constraints

Twistopher II was designed around three main constraints, two of which were entirely self-imposed, and one which was actually quite sensible.

### 1. Single-Motor Cube Manipulation

Only **one stepper motor** could be used to rotate the faces of the Rubik's Cube.

Other actuators were allowed, provided they didn't directly manipulate the cube. In this case, a servo moves the stepper motor along a rail, allowing it to engage with different gears and selectively drive different faces.

### 2. No Cube Reorientation

The Rubik's Cube must maintain the same overall orientation throughout the entire process, from scanning to solving.

Individual faces can rotate, of course, but the cube itself cannot be repositioned or reoriented to give the motor access to different sides.

Combined with the single-motor requirement, this meant finding a way to mechanically distribute rotation from one motor to multiple faces of a stationary cube.

### 3. Ease of Use and Cube Compatibility

Despite the intentionally impractical mechanical constraints, I wanted the robot to be as straightforward to use as possible.

The user should be able to take an ordinary, scrambled Rubik's Cube, place it into the machine, clamp it in position, and press Start.

No modifications to the cube, no special attachments, and no complicated setup.

I also wanted the mechanism to accommodate as many different standard-sized Rubik's Cubes as reasonably possible, rather than requiring a specific cube designed for the robot.

### An Additional Design Decision: Five-Face Operation

One important decision that emerged during development was to leave the top face of the cube mechanically undriven.

This simplified the mechanism considerably and provided an open area for inserting and removing the cube, as well as positioning the camera for scanning.

It also meant that the robot could only rotate five of the six faces, requiring a solving algorithm capable of working within that limitation.

The five-face restriction wasn't part of the original challenge. It was simply a design decision that made the rest of the machine a little less ridiculous to build.


## Mechanical Design and CAD

*[Insert full CAD assembly render]*

The mechanical design is a central focus of Twistopher II.

This section documents the development of the mechanisms, the CAD modelling process, the design iterations and the manufacturing of the physical components.

- **CAD software:** [To be added]
- **Manufacturing methods:** [To be added]
- **Key mechanisms:** [To be added]

### Design Development

*[Insert CAD screenshots, mechanism diagrams and design iterations]*

---

## Electronics and Control

*[Insert electronics photograph or wiring diagram]*

This section describes the electronic components, motor-control system and integration between the controller and the mechanical assembly.

- **Microcontroller:** [To be added]
- **Motor and driver:** [To be added]
- **Additional electronics:** [To be added]

---

## Software

This section covers the software used to control the robot, coordinate mechanical operations and implement the cube-solving process.

- **Programming languages:** [To be added]
- **Control architecture:** [To be added]

Source code will be provided in this repository.

---

## Build and Demonstration

*[Insert photographs of the physical assembly]*

**Demonstration video:** [Link to be added]

This section will document the assembly process, testing, performance and remaining limitations.

---

## Project Files

- CAD models and assemblies
- 3D-printing files
- Electronic control code
- Wiring documentation
- Build photographs and demonstrations

---

## Future Development

[Planned improvements and remaining challenges to be added.]

---

*Twistopher II is a personal engineering project exploring what happens when mechanical creativity takes priority over practical efficiency.*
