---
name: motion-graphics
description: Expert motion design and animation engineering covering animation principles (easing, timing, anticipation, follow-through, squash and stretch), keyframing techniques, 2D and 3D motion graphics, video compositing, kinetic typography, After Effects workflows, Lottie animation export, and CSS/WebGL animation implementation. Produces performant animated deliverables.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: motion-design
  triggers: motion graphics, motion design, animation, keyframe, easing, timing, kinetic typography, After Effects, Lottie, CSS animation, 2D animation, 3D animation, video compositing, animated explainer, transition, micro-interaction
  role: specialist
  scope: implementation
  output-format: code
  related-skills: graphic-design, ui-design, frontend-ui-engineering, framer-motion, video-use
---

# Motion Graphics

Senior motion design and animation specialist producing compelling, performant motion graphics for digital products, brand video, explainer content, and interactive interfaces.

## When to Use This Skill

- Creating animated brand videos, explainers, title sequences, and promotional content
- Designing micro-interactions and UI transitions for digital products and applications
- Building Lottie animations for lightweight cross-platform motion in mobile and web apps
- Developing kinetic typography for lyric videos, social media content, and title cards
- Animating data visualizations to reveal information progressively and engagingly
- Producing video composites: green screen keying, rotoscoping, tracking, matchmoving, color grading
- Implementing CSS, WebGL, or Canvas animations for performant browser-based motion

## Key Capabilities

- Animation principles: easing curves, timing and spacing, anticipation, follow-through, overlap, squash and stretch, arcs, secondary action
- Keyframing mastery: manual keyframe placement, roving keyframes, value graphs, speed graphs, interpolation modes
- 2D motion graphics: shape layers, masks, track mattes, parenting, precomposing, expression controls
- 3D motion graphics: 3D layers, cameras, lights, depth of field, 3D text extrusion, C4D integration, Element 3D
- Video compositing: color correction, keying (luma, chroma, difference), rotoscoping, stabilization, tracking, motion blur
- Kinetic typography: type animation, text animators, per-character transforms, range selectors, text on paths
- After Effects workflow: expressions (JavaScript), render queue, Adobe Media Encoder, dynamic link, scripts, templates
- Lottie and Bodymovin: export settings, layer compatibility, expression limitations, size optimization, playback configuration
- Web motion: CSS transitions and animations, WebGL (Three.js, GSAP), Canvas API, SVG animation, performance profiling

## Core Principles

### The 12 Principles of Animation
- **Squash and stretch**: Give objects weight and flexibility by deforming them during movement
- **Anticipation**: Prepare the audience for an action with a preparatory movement (wind-up, crouch)
- **Staging**: Present an idea clearly — composition, timing, and camera angle should make the intent unmistakable
- **Straight ahead and pose-to-pose**: Straight ahead for fluid, organic motion; pose-to-pose for controlled, planned animation
- **Follow-through and overlapping action**: Different parts of an object continue moving after the main motion stops
- **Slow in and slow out**: Add more frames at the beginning and end of an action for natural acceleration and deceleration
- **Arcs**: Most natural motion follows a curved path; avoid mechanical straight-line movement
- **Secondary action**: Supporting movements that enrich the main action without overwhelming it
- **Timing**: Number of frames determines speed and weight; fewer frames = faster, more frames = slower and heavier
- **Exaggeration**: Push movement beyond reality for clarity, humor, or dramatic effect without losing believability
- **Solid drawing**: Apply principles of 3D space, weight, balance, and anatomy to 2D animation
- **Appeal**: Characters and motion should be pleasing to watch — clear silhouettes, engaging design, compelling movement

### Easing and Timing
- **Linear**: Mechanical, constant speed — use only for camera movements or robotic motion
- **Ease-in**: Accelerates from rest — good for objects leaving the viewer's focus
- **Ease-out**: Decelerates to rest — good for objects entering or settling into position
- **Ease-in-out**: Accelerates and decelerates — natural for most UI transitions and object motion
- **Custom easing**: Cubic bezier curves for brand-specific motion signatures (e.g., elastic, bounce, overshoot)
- **Timing reference**: 24fps for film, 30fps for broadcast, 60fps for web and UI animation

### Kinetic Typography
- Motion should reinforce the meaning and emotion of the text, not distract from it
- Animate in order of priority: first the overall message, then individual words, then character details
- Match pacing to the voiceover or audio rhythm — motion hits should align with stressed syllables
- Use scale, opacity, position, and rotation as primary properties; avoid overcomplicating with excessive effects

### Web and UI Motion
- Duration: UI animations should complete within 200–500ms; longer feels sluggish
- Performance: use GPU-accelerated properties (transform, opacity) — avoid animating layout-triggering properties (width, height, top, left)
- Reduced motion: respect prefers-reduced-motion by providing static alternatives or simplified animations
- Purpose: every animation must serve a function — feedback, orientation, spatial relationship, or brand expression

## Practical Workflows

### 1. Animate a Logo Reveal
1. Import the logo as separate layers (icon, wordmark, tagline) and set initial positions off-screen
2. Apply ease-out position keyframes with staggered delays (icon first, wordmark 8 frames later, tagline 16 frames)
3. Add a subtle scale bounce on settle and a light particle or glow effect that fades out over the final second

### 2. Create a Kinetic Typography Sequence
1. Import the voiceover audio and create markers on stressed syllables or beat hits
2. Animate text in blocks using opacity and position, matching each phrase to its corresponding audio segment
3. Add per-character range selector animation on key words for emphasis, easing each one with a custom bezier curve

### 3. Build a UI Micro-Interaction for Handoff
1. Identify the trigger (tap, hover, swipe) and define the animation's purpose (feedback, state change, navigation)
2. Create an After Effects composition at 60fps with the UI frame, animate the interaction using transform and opacity only
3. Export as Lottie JSON, test on the target device, and provide developers with the trigger timing and easing function values

### 4. Composite a Green Screen Interview
1. Apply the Keylight effect on the green screen footage, sample the screen color, adjust clip black/white levels for clean edges
2. Add the background plate, apply a slight blur (2–4px) to the background for depth, and match grain between layers
3. Color grade the foreground to match background lighting, add a subtle shadow on the floor for grounding, and render with alpha

### 5. Develop a CSS Loading Spinner
1. Define the spinner geometry as a circular track with a translucent background and a solid accent arc
2. Animate the arc's rotation with a 1s linear infinite cycle using CSS transform: rotate()
3. Add a secondary counter-rotation or color shift on the arc for visual interest, respect prefers-reduced-motion by using a static pulse

## Best Practices

- Establish a motion design system with standardized easing curves and durations before animating individual elements; consistency creates a cohesive brand feel across all motion output.
- Use the After Effects graph editor (speed graph for spatial properties, value graph for temporal) rather than relying on default keyframe interpolation — custom curves define the quality of your animation.
- When exporting Lottie animations, test on target devices early in production; verify that expressions, effects, and third-party plugins are compatible or baked into keyframes.

## Technical Specifications

| Output | Format | Frame Rate | Codec | Resolution |
|--------|--------|------------|-------|------------|
| Social Media | MP4/H.264 | 30fps | H.264 | 1080×1080, 1080×1920 |
| Broadcast | ProRes 422 | 23.976fps | ProRes | 1920×1080 |
| Web (Lottie) | JSON | 30fps | Bodymovin | Vector |
| Web (CSS) | CSS/JS | 60fps | GPU-composite | Viewport-based |
| Cinema | ProRes 4444 | 24fps | ProRes | 3840×2160 |

## Quality Checklist

- Animation serves a clear purpose (feedback, orientation, narrative, or brand expression)
- Easing curves are custom-tuned, not default linear
- Timing feels natural for the medium (UI < 500ms, narrative matches audio pacing)
- Follow-through and overlap applied to secondary elements
- Lottie animations are tested on target devices and optimized for file size
- Web animations use only GPU-composited properties (transform, opacity)
- Reduced motion alternative is provided for accessibility
- Composition has clear staging and visual hierarchy
- Color, typography, and motion style align with brand guidelines
