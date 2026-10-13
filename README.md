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

The mechanical design was by far the biggest challenge of Twistopher II, and easily the part of the project I spent the most time on.

Almost the entire machine was designed from scratch in Fusion 360, from the gear trains and motor-selection mechanism to the structural supports and cube-holding assemblies.

The challenge wasn't simply getting a motor to turn a Rubik's Cube face. It was figuring out how to take rotational motion from a single motor, selectively distribute it to five different outputs, and then route that motion around the cube to five different faces.

All while keeping the cube in the same orientation.

**[IMAGE: Full Fusion 360 assembly, preferably an isometric view showing the entire mechanism]**

### 1. Designing the Gear-Selection Mechanism

The first problem I tackled was figuring out how to get a single NEMA 17 stepper motor to independently drive five different outputs.

The key requirement was that when one output was engaged, the other four had to remain stationary.

After plenty of sketches and abandoned CAD designs, I settled on a system that works somewhat like a gearbox, except instead of selecting different gear ratios, it selects where the motor's rotational power is delivered.

Four output gears are arranged around a larger central driving gear. However, rather than placing all four on the same plane, each output gear is offset by a different distance along the motor's axis.

The central gear, attached to the stepper motor, moves forwards and backwards along this axis. Depending on its position, it meshes with one of the four output gears.

This allows the same motor to drive four separate mechanisms without engaging all of them simultaneously.

**[DIAGRAM 1: Simplified illustration of the central driving gear and four surrounding output gears, each offset along the motor's axis. Use different colours to distinguish the four engagement positions.]**

The fifth output, which controls the front face, uses a completely different approach.

Instead of relying on gear teeth, I added a small hexagonal shaft protruding from the centre of the stepper's driving gear. When the stepper moves to its furthest-forward position, this shaft slots into a matching hexagonal socket connected to the front-face transmission.

Rotating the stepper then rotates the front-face mechanism directly through this coupling.

This turned out to be a particularly useful design decision. It meant I could fit the fifth output into an already crowded mechanism without needing another gear to mesh with the central driving gear.

**[IMAGE / DIAGRAM 2: Side-by-side illustration of the two engagement methods: conventional gear meshing versus the hexagonal shaft-and-socket coupling.]**

The stepper motor itself is mounted on a linear rail and repositioned using an MG995 servo motor.

Strictly speaking, that means the machine contains two motors. However, only the stepper motor actually rotates the cube's faces. The servo simply selects which transmission the stepper drives.

### 2. Routing Torque Around the Cube

Once I had five independently selectable outputs, the next challenge was getting their rotational motion to the corresponding cube faces.

This turned out to be significantly more complicated than I initially anticipated.

The output gears were positioned too close together for their shafts to pass around the cube. One solution would have been to use much larger gears to increase the spacing, but this would have made the mechanism unnecessarily bulky.

Instead, I developed a three-gear transmission arrangement that allowed the drive shafts to be positioned further apart while also providing an opportunity for gear reduction.

**[DIAGRAM 3: Comparison of the original tightly spaced output shafts and the expanded shaft spacing achieved using the three-gear transmission.]**

From there, a combination of shafts, spur gears and bevel gears carries the rotation around the cube to the individual faces.

Bevel gears were particularly useful because they allowed me to redirect rotational motion through changes in shaft orientation.

Some of the transmissions are relatively straightforward. Others, particularly those driving the rear and bottom faces, became considerably more complicated.

The rear-face transmission, for example, routes motion underneath the cube before redirecting it through multiple bevel-gear arrangements to reach the required axis of rotation.

**[IMAGE 4: Close-up CAD screenshot of the rear-face transmission, with arrows tracing the route taken by the rotational motion.]**

**[IMAGE 5: Close-up CAD screenshot of the bottom-face transmission.]**

Getting these mechanisms to fit together without interfering with one another required a considerable amount of CAD work, and was probably the most challenging aspect of the entire mechanical design.

### 3. Gear Ratios and Torque Calculations

One issue I identified early on was that the NEMA 17 stepper motor had relatively little torque to spare at the operating speed I wanted.

Rather than simply guessing whether it would be sufficient, I attempted to estimate the torque needed to turn a Rubik's Cube face experimentally.

Using a luggage scale attached to a string, I measured the approximate force required to overcome the cube's turning resistance. From this, I could estimate the required torque using the distance between the applied force and the axis of rotation.

The measurements were fairly crude, but they gave me a useful starting point.

I then designed the transmission to provide approximately twice the estimated torque requirement.

This was partly to accommodate different cubes, particularly those with stronger magnets or stiffer turning mechanisms, but also to provide some tolerance for mechanical imperfections.

For example, if the stepper missed steps or a component became slightly loose, a cube face might end up marginally misaligned. With very little torque to spare, even a small increase in resistance could stall the mechanism and ruin the solve.

The additional torque margin was intended to help the machine tolerate minor resistance and alignment errors, although it obviously cannot guarantee recovery from a genuinely jammed mechanism.

The final transmission uses three gear-ratio stages:

| Stage | Ratio | Effect |
|---|---|---|
| A | 3:4 | 1.33× speed increase |
| B | 2:1 | 2× speed reduction |
| C | 2:1 | 2× speed reduction |
| **Overall** | **3:1** | **3× speed reduction** |

This means a **270° rotation of the stepper motor produces a 90° rotation of the cube face**.

Ignoring mechanical losses, the overall reduction also increases the available output torque by a factor of three.

**[DIAGRAM 6: Simple three-stage gear-ratio diagram showing 270° → 360° → 180° → 90°.]**

The gear ratios were therefore not just about getting the correct angular movement. They were also an important part of ensuring the mechanism had sufficient torque to operate reliably.

### 4. Learning from Twistopher I

Twistopher II was not my first attempt at this project.

The original Twistopher was, to put it politely, a bit of a disaster.

My initial approach was almost entirely trial and error: design something, 3D print it, see if it worked, and then design the next part around whatever I'd already made.

This worked reasonably well at the beginning, but created increasingly difficult problems as the assembly grew.

Every early design decision restricted the options available later. By the time I reached the final mechanisms, I had already committed to so many dimensions and component positions that finding workable solutions became incredibly difficult.

The original machine suffered from just about everything you could imagine: excessive backlash, insufficient torque, flexing, wobbling, poor gear engagement and mechanisms that would regularly jam.

I also relied far too heavily on hot glue, which made disassembly, repairs and modifications unnecessarily difficult.

Eventually, I abandoned the first design and started again.

**[IMAGE 7: Photograph or CAD screenshot of the original Twistopher I, ideally compared with Twistopher II.]**

The biggest lesson I took from that failure was the importance of developing a sufficiently complete CAD design before committing to manufacturing.

For Twistopher II, I approached things very differently.

Rather than printing each new component as soon as I designed it, I spent considerably more time developing the full assembly in Fusion 360.

I worked through the mechanisms, checked clearances, incorporated the relevant components and developed the design until I had a complete assembly that I was confident could actually be built.

This didn't eliminate physical testing, but it made the testing much more purposeful.

For components with particularly critical dimensions or tolerances, I printed small test pieces first. Once I was satisfied that the parts fitted and functioned correctly, I could commit to printing the larger components without wasting unnecessary material.

The result was a dramatically smoother manufacturing and assembly process, with far fewer major redesigns needed.

If there's one lesson I took away from the entire project, it's that spending more time developing a good CAD design can save an extraordinary amount of time, material and frustration later.

### 5. Manufacturing and Assembly

Almost every custom mechanical component in Twistopher II was 3D printed, including the gears, structural supports, motor mounts and various transmission components.

However, some components were better purchased than manufactured.

The main hardware included:

- **NEMA 17 stepper motor** — primary cube-face actuation
- **MG995 servo motor** — stepper-position selection
- **Aluminium shafts** — purchased and cut to the required lengths
- **Bearings** — support for rotating shafts and mechanisms
- **Linear rail and slider** — smooth, low-friction movement of the stepper assembly
- **Approximately 50 nuts and bolts** — primarily M3 fasteners
- **Custom 3D-printed components** — gears, brackets, supports and mechanical assemblies

I deliberately chose to use a purchased linear rail rather than attempting to 3D print the sliding mechanism, as the friction and wear associated with a printed sliding system would have made reliable gear engagement more difficult.

Another major change from Twistopher I was designing the assembly around **screws and bolts rather than glue**.

Almost every component can be removed and replaced individually without damaging the surrounding structure.

This proved particularly useful during testing and maintenance. If a printed component broke or needed adjusting, I could simply remove the relevant fasteners, replace the part and reassemble the mechanism.

Very little glue was used, aside from occasional minor repairs.

**[IMAGE 8: Photograph of the partially assembled robot, showing the shafts, bearings, fasteners and structural components.]**

### 6. A Very Important Design Decision: The Colour Scheme

A surprising amount of thought also went into the colour scheme.

All moving components, including the gears, were printed in yellow, while the stationary structural components were printed in black.

This made the moving mechanisms easier to distinguish and gave the machine a rather satisfying industrial appearance, somewhere between a JCB and a DeWalt power tool.

There were, however, two slightly less technical reasons.

Firstly, the original Twistopher I had been orange and white, and after that project's spectacular failure, I decided the colour scheme was clearly cursed.

Secondly, I had always imagined making a YouTube video of the finished machine solving a cube with *Black and Yellow* by Wiz Khalifa playing in the background.

Unfortunately, I later discovered how YouTube copyright works.

So the robot kept its colour scheme, but the soundtrack didn't quite survive the design process.

**[IMAGE 9: Photograph of the completed yellow-and-black Twistopher II.]**

### Final Thoughts on the Mechanical Design

Of everything I worked on throughout this project, the mechanical design is probably what I'm most proud of.

Twistopher II was easily one of the most complicated things I'd attempted to design from scratch, and it pushed my understanding of CAD, gears, mechanical transmissions, tolerances and manufacturing far beyond where it had been before.

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
