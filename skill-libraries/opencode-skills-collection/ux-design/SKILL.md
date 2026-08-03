---
name: ux-design
description: Expert user experience design grounded in human-centered design methodology covering user research, usability testing, information architecture, user journey mapping, persona development, wireframing, interaction design, WCAG accessibility compliance, and mental model analysis. Produces research-backed design solutions.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: experience-design
  triggers: UX design, user experience, user research, usability testing, information architecture, user journey, persona, wireframe, interaction design, accessibility, WCAG, mental model, human-centered design, user flow, experience strategy
  role: specialist
  scope: implementation
  output-format: code
  related-skills: ui-design, graphic-design, motion-graphics, feature-forge, design-ux-research
---

# UX Design

Senior user experience design specialist applying human-centered design processes to create intuitive, accessible, and effective digital products backed by qualitative and quantitative research.

## When to Use This Skill

- Conducting user research to uncover needs, behaviors, pain points, and mental models
- Designing and facilitating usability testing sessions to validate design decisions
- Structuring information architecture for complex applications, websites, or content platforms
- Mapping user journeys, service blueprints, and experience flows for multi-touchpoint products
- Creating research-backed personas and scenarios to guide design decisions
- Wireframing and prototyping interaction flows from low-fidelity to high-fidelity
- Ensuring accessibility compliance through inclusive design practices and WCAG standards

## Key Capabilities

- User research methods: interviews, surveys, contextual inquiry, diary studies, card sorting, tree testing, A/B testing
- Usability testing: test plan creation, moderator guides, task design, remote and in-person moderation, findings synthesis
- Information architecture: content inventory, sitemaps, navigation design, labeling systems, search optimization, taxonomy
- Journey mapping: empathy maps, customer journey maps, experience maps, service blueprints, pain point identification
- Persona development: data-driven archetypes, goals, motivations, frustrations, behavioral segments, scenarios
- Wireframing and prototyping: sketch to Figma, fidelity progression, click-through prototypes, design iteration
- Interaction design: micro-interactions, gesture design, feedback loops, state transitions, animation intent
- Accessibility (WCAG): perceivable, operable, understandable, robust principles; assistive technology compatibility

## Core Concepts

### Human-Centered Design Process
- **Empathize**: Understand the user through research — their environment, challenges, goals, and emotional state
- **Define**: Synthesize research findings into a clear problem statement and design criteria
- **Ideate**: Brainstorm multiple solutions without judgment, then converge on promising directions
- **Prototype**: Create low-fidelity to high-fidelity representations of the solution for testing
- **Test**: Validate with real users, collect feedback, and iterate based on evidence

### Mental Models
- Users bring pre-existing mental models from other products and real-world experiences
- Design should align with users' mental models rather than forcing them to learn new paradigms
- Use familiar patterns (shopping cart, hamburger menu, swipe gestures) to reduce cognitive load
- When introducing novel interactions, provide onboarding and progressive disclosure

### Information Architecture
- Content should be organized according to users' mental models, not the organization's internal structure
- Use card sorting (open and closed) to discover how users naturally categorize information
- Implement clear, consistent navigation labeling; avoid jargon and internal terminology
- Support wayfinding with breadcrumbs, clear page titles, and persistent navigation landmarks

### Accessibility as UX
- Accessibility is not a checklist — it is a fundamental aspect of user experience
- Inclusive design expands the product's reach and improves usability for all users (curb-cut effect)
- Involve users with disabilities in research and testing throughout the design process
- Design for diverse abilities: vision, hearing, motor, cognitive, and speech considerations

## Practical Workflows

### 1. Plan and Conduct User Interviews
1. Define research goals and craft a discussion guide with open-ended questions and follow-up probes
2. Recruit 5–8 participants matching the target persona, schedule 45–60 minute sessions with consent forms
3. Conduct interviews via video call, take structured notes or record (with permission), and debrief after each session to capture top insights

### 2. Facilitate a Card Sorting Session
1. Generate 30–60 content items from the sitemap or content inventory, each written on a separate card
2. Run an open card sort (users create their own categories) with 15–20 participants using a remote tool
3. Analyze results with a dendrogram or similarity matrix to identify consensus groupings for navigation structure

### 3. Perform a Heuristic Evaluation
1. Recruit 3–5 evaluators and provide them with Nielsen's 10 usability heuristics and a list of user tasks
2. Each evaluator independently inspects the interface and records violations with severity ratings (0–4)
3. Aggregate findings, calculate average severity, and prioritize fixes by severity × frequency for the remediation roadmap

### 4. Create a Customer Journey Map
1. Identify the persona, scenario, and phase boundaries (awareness, consideration, purchase, support, retention)
2. For each phase, list user actions, touchpoints, emotions, pain points, and opportunities
3. Validate the map with stakeholder review and real-user feedback, then identify moments of truth for design focus

### 5. Run a Usability Test
1. Write 5–8 task scenarios that cover core user goals, with measurable success criteria for each
2. Pilot the test with one participant to refine tasks and the moderator script, then run sessions with 5 users per round
3. Analyze task completion rates, time on task, error counts, and severity of issues; produce a findings report with video highlights

## Best Practices

- Test with real users early and often — a prototype tested with 5 users uncovers 85% of usability issues before a single line of code is written.
- Synthesize research findings collaboratively using affinity mapping; individual interpretation introduces bias that group analysis can correct.
- Design for the edge cases first — error states, empty states, and accessibility needs — then layer in the happy path.

## Research and Validation Methods

| Method | Phase | Purpose |
|--------|-------|---------|
| Contextual Inquiry | Empathize | Observe users in their natural environment |
| Card Sorting | Define | Understand user mental models for information organization |
| Usability Testing | Test | Validate designs with task-based observation |
| A/B Testing | Iterate | Compare two design variants quantitatively |
| Tree Testing | Define | Evaluate findability of navigation labels |
| Diary Study | Empathize | Capture in-context behaviors over time |

## Quality Checklist

- Research methods match the design question (generative vs evaluative vs behavioral)
- At least 5 users tested per usability study round
- Personas are grounded in real data, not assumptions
- Journey maps include emotional highs and lows, not just actions
- Wireframes are tested before visual design begins
- Navigation labels are tested for clarity with card sorting
- Accessibility is evaluated with both automated tools and manual testing
- Design decisions are traceable back to research findings
