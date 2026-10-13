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
