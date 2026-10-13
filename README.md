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

The mechanical design was by far the biggest challenge of Twistopher II, and easily the part of the project I spent the most time on. Almost the entire machine was designed from scratch in Fusion 360, from the gears and transmission mechanisms to the structural supports and cube-holding assemblies.

The challenge wasn't simply getting a motor to turn a Rubik's Cube face. It was figuring out how to take rotational motion from a single motor, independently distribute it to five different outputs, and then route that motion around the cube to five different faces, all without ever reorienting the cube itself.

*[IMAGE: Full Fusion 360 assembly — isometric view]*

### The Gear-Selection Mechanism

The first problem I tackled was figuring out how to get a single NEMA 17 stepper motor to independently drive five different outputs. The key requirement was that when one output was engaged, the other four had to remain stationary.

After plenty of sketches and abandoned designs, I settled on a mechanism that works somewhat like a gearbox. However, rather than changing the gear ratio, it changes where the motor's rotational power is delivered.

Four output gears are arranged around a larger central driving gear, but instead of all being positioned on the same plane, each one is offset by a different distance along the motor's axis. The central gear, attached to the stepper motor, can slide forwards and backwards along this axis. By moving to different positions, it engages with one of the four output gears while leaving the others disengaged.

*[DIAGRAM: Four output gears positioned at different axial depths around the central driving gear. Show the central gear sliding between engagement positions.]*

The fifth output, which controls the front face, uses a different approach. Instead of relying on the teeth of the central gear, I added a small hexagonal shaft protruding from its centre. When the stepper moves to its furthest-forward position, this shaft slides into a matching hexagonal socket connected to the front-face transmission. Rotating the motor then drives the front face directly through this coupling.

This turned out to be one of my favourite design decisions. It meant I could fit a fifth output into an already crowded mechanism without trying to squeeze in another gear engagement.

*[IMAGE/DIAGRAM: Close-up of the hexagonal shaft-and-socket coupling.]*

The stepper motor is mounted on a linear rail and moved between these engagement positions using an MG995 servo motor. Strictly speaking, this means Twistopher II contains two motors, but only one actually rotates the cube's faces. The servo simply selects which transmission the stepper drives.

### Routing Torque Around the Cube

Once I had five independently selectable outputs, the next challenge was getting their rotational motion to the corresponding cube faces. This turned out to be considerably more complicated than I originally expected.

The output gears were positioned too close together for their shafts to pass around the cube. One possible solution was to make the gears much larger, increasing the distance between their centres, but this would have resulted in an unnecessarily bulky and rather ridiculous-looking mechanism. Instead, I developed a three-gear arrangement that allowed the shafts to be positioned further apart while also incorporating gear reduction.

*[DIAGRAM: Comparison between the original closely spaced shafts and the expanded shaft spacing achieved using the three-gear arrangement.]*

From there, the rotational motion had to be routed around the cube using combinations of shafts, spur gears and bevel gears. The bevel gears were particularly important because they allowed the direction of rotation to be redirected through changes in shaft orientation.

Some transmissions were relatively straightforward, while others became considerably more complicated. The rear-face transmission, for example, routes motion underneath the cube before passing through multiple bevel-gear arrangements to reach the rear face at the correct angle. The bottom-face transmission presented similar challenges.

*[IMAGE: CAD close-up of the rear-face transmission, with arrows showing the path taken by the rotational motion.]*

*[IMAGE: CAD close-up of the bottom-face transmission.]*

Getting all these mechanisms to fit together without interfering with one another required a considerable amount of work in Fusion 360. It was probably the most challenging part of the entire mechanical design, but also one of the most satisfying once everything finally fitted together.

### Gear Ratios and Torque

One issue I identified during development was that the NEMA 17 stepper motor had relatively little torque to spare at the operating speed I wanted. Rather than simply guessing whether it would be sufficient, I decided to estimate the torque required to turn a Rubik's Cube face experimentally.

Using a luggage scale attached to a string, I measured the approximate force required to overcome the cube's turning resistance. From this, I could estimate the required torque using the distance between the applied force and the axis of rotation. The measurements and calculations were fairly crude, but they provided a useful starting point.

I deliberately aimed to design the transmission to provide roughly twice the estimated torque requirement. This wasn't just to accommodate different cubes, including those with stronger magnets or stiffer turning mechanisms. I also wanted to give the robot some tolerance for things going slightly wrong.

For example, if the stepper missed a few steps, a component loosened, or a cube face ended up slightly misaligned, this could introduce additional resistance during the next move. With very little torque to spare, even a small error could stall the mechanism and ruin the solve. The additional torque margin was intended to help the machine tolerate minor mechanical imperfections rather than immediately giving up. Of course, extra torque isn't a guaranteed solution to a genuinely jammed mechanism, but it provides some useful breathing room.

The final transmission uses three gear-ratio stages: an initial **3:4 speed increase**, followed by two **2:1 gear reductions**. Together, these produce an overall **3:1 reduction**, meaning that a 270° rotation of the stepper motor results in a 90° rotation of the cube face.

| Stage | Gear Ratio | Effect |
|---|---|---|
| A | 3:4 | 1.33× speed increase |
| B | 2:1 | 2× speed reduction |
| C | 2:1 | 2× speed reduction |
| **Overall** | **3:1** | **3× speed reduction** |

Ignoring mechanical losses, this also provides a theoretical threefold increase in output torque compared with the stepper motor's input torque.

*[DIAGRAM: Three-stage gear transmission showing 270° → 360° → 180° → 90°.]*

### Learning From Twistopher I

Twistopher II was not my first attempt at this project. The original Twistopher was, to put it politely, a bit of a disaster.

My initial approach was almost entirely trial and error. I'd design a component, 3D print it, test whether it worked, and then design the next part around whatever I'd already made. This worked reasonably well at first, but created increasingly difficult problems as the assembly grew. Every early decision restricted what I could do later, and by the time I was designing the final mechanisms, I'd already committed to so many dimensions and component positions that finding workable solutions became incredibly difficult.

The original machine suffered from just about everything you could imagine: excessive backlash, insufficient torque, flexing, wobbling, poor gear engagement and mechanisms that would regularly jam. I also relied far too heavily on hot glue, which made disassembly, modifications and repairs unnecessarily difficult.

Eventually, I decided to abandon the first design and start again.

*[IMAGE: Twistopher I — photograph or CAD screenshot of the original unsuccessful prototype.]*

The biggest lesson I took from that failure was the importance of developing a sufficiently complete CAD design before committing to manufacturing. I'd heard the phrase "measure twice, cut once" plenty of times before, but this project really made me appreciate what it meant.

For Twistopher II, I approached the design process very differently. Instead of printing each component as soon as I'd designed it, I spent considerably more time developing the full assembly in Fusion 360. I learned a great deal about modelling, component joints, motion links, designing spur and bevel gears, and incorporating imported CAD models of purchased components such as the stepper and servo motors.

More importantly, I learned how to use CAD to make better engineering decisions before committing to them physically. By the time I started manufacturing the final version, I already had a complete assembly designed on my computer, with the major mechanisms and component positions worked out.

This didn't eliminate physical testing, but it made the testing much more purposeful. For components with critical dimensions or tolerances, I printed small test pieces first to check that everything fitted as intended. Only once I was satisfied would I commit to printing the larger components, saving material and avoiding unnecessary reprints.

The result was a dramatically smoother manufacturing and assembly process, with far fewer major redesigns needed. If there's one lesson I took away from the project, it's that spending more time developing a good CAD design can save an extraordinary amount of time, material and frustration later.

### Manufacturing and Assembly

Almost every custom mechanical component in Twistopher II was 3D printed, including the gears, structural supports, motor mounts and various transmission components. However, there were some parts that made much more sense to purchase rather than manufacture.

The rotating shafts were made from purchased aluminium rods, which I cut to the required lengths. I also used purchased bearings, a NEMA 17 stepper motor and an MG995 servo motor. For the stepper's sliding mechanism, I chose a commercially available linear rail and slider rather than attempting to 3D print one, as a printed sliding system would likely introduce excessive friction and wear.

Another major improvement over Twistopher I was designing the entire assembly around screws and bolts rather than glue. The finished robot uses approximately 50 nuts and bolts, primarily M3 fasteners, allowing almost every component to be removed and replaced individually.

This made testing, maintenance and repairs much easier. If a printed component broke or needed adjusting, I could simply undo the relevant fasteners, replace the part and reassemble the mechanism without damaging everything around it. Very little glue was used, aside from occasional minor repairs.

*[IMAGE: Partially assembled Twistopher II, showing the shafts, bearings, fasteners and internal mechanisms.]*

### A Very Important Design Decision: The Colour Scheme

A surprising amount of thought also went into the colour scheme.

All moving components, including the gears, were printed in yellow, while the stationary structural components were printed in black. This made the moving mechanisms easier to distinguish and gave the whole machine a rather satisfying industrial appearance, somewhere between a JCB and a DeWalt power tool.

There were, however, two slightly less technical reasons for this decision.

Firstly, the original Twistopher I had been orange and white, and after that project's spectacular failure, I decided the colour scheme was clearly cursed.

Secondly, I had always imagined making a YouTube video of the finished machine solving a cube with *Black and Yellow* by Wiz Khalifa playing in the background.

Unfortunately, I later discovered how YouTube copyright works.

So the robot kept its colour scheme, but the soundtrack didn't quite survive the design process.

*[IMAGE: Completed yellow-and-black Twistopher II.]*

### Final Thoughts

Of everything I worked on throughout this project, the mechanical design is probably what I'm most proud of. Twistopher II was easily one of the most complicated things I'd attempted to design from scratch, and it pushed my understanding of CAD, gears, mechanical transmissions, tolerances and manufacturing far beyond where it had been before.

More importantly, it completely changed how I approach designing and building physical projects.

What began as an attempt to avoid buying a few extra motors eventually turned into a much larger exercise in mechanical engineering.

And somehow, despite making the problem considerably harder than it needed to be, the finished machine actually works.

---


## Electronics and Control

Compared with the mechanical design, the electronics of Twistopher II were relatively straightforward. Most of the components were ones I'd already worked with on previous projects, although this was my first time properly using an ESP32.

The main controller is an **ESP32 Dev Module**, responsible for controlling a NEMA 17 stepper motor and an MG995 servo motor. The stepper is driven using a **TMC2209 stepper motor driver**, which I chose partly for its quiet operation and partly because I happened to have one left over from an earlier project.

The entire system is powered by a **24V, 3A power supply**. The stepper driver operates from the 24V supply, while a DC-DC buck converter steps the voltage down to 6V for the servo motor. I also added 100µF capacitors across the power inputs of both the stepper driver and servo supply to help with voltage fluctuations.

Everything was assembled using jumper wires and a modified breadboard. The breadboard actually needed modifying because the ESP32 was too wide to conveniently access all its pins using a standard breadboard arrangement. There was no custom PCB involved, although designing one would certainly make the electronics considerably neater.

*[IMAGE: Photograph of the ESP32, TMC2209, buck converter and breadboard wiring.]*

### Motor Control

The ESP32 generates STEP and DIR signals for the TMC2209 driver, allowing it to control the stepper motor's movement and direction.

The servo is responsible for moving the entire stepper assembly along its linear rail. During development, I determined and recorded five specific servo positions, each corresponding to a different gear engagement.

When the ESP32 receives a command to rotate a particular cube face, it first moves the servo to the corresponding position. After a short delay to allow the mechanism to engage, it commands the stepper motor to perform the required rotation.

Because of the overall 3:1 gear reduction, a **270° stepper rotation produces a 90° cube-face turn**, while a 540° rotation produces a 180° turn. Reversing the stepper's direction allows the face to rotate in the opposite direction.

The ESP32 communicates with the computer over a USB serial connection. The USB camera is connected directly to the computer, allowing the PC to handle image processing and solution calculation while the ESP32 handles the physical motor movements.

### Solving the Backlash Problem

One of the most frustrating problems during development was caused by backlash in the 3D-printed gears.

Even with carefully designed components, the printed gears couldn't have perfect tolerances. This meant that once the stepper disengaged from a gear, that gear could rotate slightly within the available backlash, particularly due to vibrations from the moving assembly.

When the stepper later attempted to pass through that gear's engagement position, the teeth might no longer be aligned correctly. Instead of sliding into engagement, the teeth could collide directly with one another.

This was a serious problem. The servo could potentially try to force the stepper assembly through an obstruction, causing the mechanism to jam, the servo to stall, or even the printed structure to crack, something I'd already encountered during the original Twistopher build.

Rather than attempting to eliminate every last bit of backlash mechanically, I developed a solution using the stepper motor itself.

**While moving between gear positions, the stepper rapidly oscillates back and forth through approximately 5°.** This creates a small vibration in the driving gear, allowing its teeth to find a suitable alignment and slip into engagement with the output gears.

Essentially, the motor gives the gears a little shimmy until they cooperate.

This turned out to work extremely well and made switching between the different gear engagements considerably more reliable.

*[DIAGRAM: Two gears with misaligned teeth, followed by the same gears engaging after the stepper's small oscillating movement.]*

This was probably the most interesting electronics-related problem I encountered, even though the underlying issue was mechanical. It was a good example of using software-controlled motor behaviour to compensate for imperfections in a physical mechanism.

---


## Software

The software for Twistopher II is split between a Python application running on a computer and C++ firmware running on the ESP32, developed using the Arduino IDE.

The computer acts as the main brain of the machine. It handles camera input, colour recognition, reconstruction of the scrambled cube, solution calculation and communication with the ESP32.

The ESP32 handles the lower-level motor control, receiving commands over USB serial and translating them into servo movements and stepper rotations.

Most of the project's control and scanning software was developed by me, while the cube-solving algorithm itself uses an existing implementation. Later in development, I also used AI assistance to build a graphical interface and help clean up and reorganise parts of the Python code.

### Scanning the Cube

One of the more interesting software challenges came from the fact that Twistopher II uses only a single camera positioned above the cube.

Rather than moving the camera or reorienting the cube, I developed a scanning process that uses sequences of face rotations to bring different coloured facelets into view.

The camera captures the eight visible facelets on the top face. The program then uses a predetermined four-move sequence to reposition other facelets onto that surface, allowing the camera to capture another set of eight colours.

By repeating the scanning sequences, the camera collects colour information for all **48 movable facelets** across six captures.

The software keeps track of how each move changes the positions of the facelets. This allows the detected colours to be mapped back to their original positions, reconstructing the full scrambled state of the cube.

*[DIAGRAM: A Rubik's Cube showing facelets being moved into the camera's field of view, with arrows illustrating the scanning sequence.]*

### An Unexpected Scanning Optimisation

Originally, after completing the scanning sequence, the machine would perform an additional four moves to return the cube to its original scrambled state before beginning the solve.

This worked perfectly well, but it also meant spending several seconds physically moving the cube for no real reason.

Eventually, I realised there was a simpler solution: instead of moving the physical cube back to match the software's representation, why not update the software's representation to match the cube?

The program already knew which moves had been performed during scanning. By accounting for the final four moves, it could calculate the cube's current state and generate a solution directly from there.

This eliminated four unnecessary physical moves and saved approximately three seconds.

A small improvement, but quite a satisfying one.

### Calculating the Solution

Once scanning is complete, the reconstructed cube state is passed to a Rubik's Cube-solving algorithm.

Most conventional solving algorithms assume that all six faces of the cube can be rotated. Twistopher II, however, only has mechanical access to five faces, with the upper face remaining fixed.

Fortunately, Herbert Kociemba, the developer of the well-known Two-Phase Rubik's Cube-solving algorithm, also developed a solver capable of finding solutions while restricting moves on one face.

This made it possible to calculate solutions that the robot could physically execute without needing to drive the sixth face.

Getting the solver working required downloading and generating access to substantial lookup tables, a process that took approximately six hours.

Once configured, the solver could calculate a valid sequence of moves using only the five available faces.

### Executing the Solution

After the solution is calculated, the Python application interprets the move sequence and sends the required commands to the ESP32 over USB serial.

For each move, the ESP32 positions the servo to engage the correct transmission, allows the mechanism to settle, and then rotates the stepper by the required amount.

The process repeats until every move in the solution has been executed.

From the user's perspective, the entire process is automatic. A scrambled cube is placed into the machine, clamped in position, and the Start button is pressed.

The machine then scans the cube, reconstructs its state, calculates a solution and executes the moves without any further intervention.

A typical complete solve takes approximately **30 seconds**, including scanning, calculation and physical execution.

*[DIAGRAM: Overall software workflow — Start → Scanning → Colour Recognition → Cube Reconstruction → Solution Calculation → Serial Commands → Motor Control → Solved Cube.]*

### Software Development

Twistopher II was developed over approximately a year, and the software evolved considerably throughout that time.

The original control logic, scanning process, cube-state tracking and communication with the ESP32 were developed as part of the project, while the actual cube-solving algorithm came from an existing implementation.

Towards the later stages, I also experimented with AI-assisted development to create a graphical user interface and improve the organisation of the Python code.

The GUI wasn't the main engineering challenge of this project, and building interfaces has never been my strongest area, so this was a useful way to make the application easier to operate without spending an unreasonable amount of time on the interface itself.

Overall, the software was a valuable learning experience, particularly in coordinating physical hardware with computer-based processing, maintaining an accurate representation of the cube's state, and solving real mechanical problems through software.


---


## Future Development

[Planned improvements and remaining challenges to be added.]

---

*Twistopher II is a personal engineering project exploring what happens when mechanical creativity takes priority over practical efficiency.*
