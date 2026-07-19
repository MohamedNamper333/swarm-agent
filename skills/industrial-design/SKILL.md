---
name: industrial-design
description: Comprehensive industrial and product design expertise covering CAD modeling, materials science and selection, ergonomics and human factors, manufacturing processes, rapid prototyping, design for manufacturing (DFM), and sustainable design practices. Produces manufacturable physical product specifications.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: product-design
  triggers: industrial design, product design, CAD, modeling, materials science, ergonomics, manufacturing, prototyping, DFM, design for manufacturing, sustainability, physical product, injection molding, 3D printing
  role: specialist
  scope: implementation
  output-format: code
  related-skills: architecture-design, industrial-design, graphic-design
---

# Industrial Design

Senior industrial and product design specialist developing physical products from concept through manufacturing, balancing aesthetics, ergonomics, materials science, and production economics.

## When to Use This Skill

- Designing physical products from concept sketches to production-ready CAD models
- Selecting appropriate materials based on mechanical properties, cost, aesthetics, and sustainability
- Applying ergonomic and human factors principles to ensure comfortable and safe product interaction
- Specifying manufacturing processes including injection molding, CNC machining, casting, and 3D printing
- Engineering designs for manufacturing efficiency, cost reduction, and quality consistency
- Creating rapid prototypes for functional testing, user validation, and stakeholder presentation
- Incorporating sustainable design principles: material reduction, recyclability, lifecycle assessment

## Key Capabilities

- CAD modeling: parametric solid modeling (SolidWorks, Fusion 360, Rhino), surface modeling, assembly design, tolerance analysis
- Materials science: polymers, metals, ceramics, composites, biomaterials — mechanical, thermal, and chemical property analysis
- Ergonomics and anthropometrics: human body measurements, reach zones, grip analysis, comfort testing, accessibility
- Manufacturing processes: injection molding, extrusion, blow molding, die casting, stamping, forging, additive manufacturing
- Design for Manufacturing (DFM): draft angles, wall thickness, rib design, boss design, gate and runner systems, tooling considerations
- Rapid prototyping: FDM, SLA, SLS, PolyJet, MJF, CNC prototyping, urethane casting, vacuum forming
- Sustainability: design for disassembly, material reduction strategies, recycled content, biodegradable alternatives, LCA
- Surface finishing: painting, plating, anodizing, powder coating, textures, graphics application, labeling

## Core Concepts

### Design for Manufacturing (DFM)
- **Draft angles**: 1–3 degrees minimum for injection molded parts to facilitate ejection from the mold
- **Uniform wall thickness**: variations cause sink marks, warpage, and uneven cooling; keep walls as uniform as possible
- **Ribs and gussets**: add strength without increasing wall thickness; rib thickness should be 50–60% of nominal wall
- **Radii and fillets**: sharp internal corners create stress concentration; use generous radii (minimum 0.5mm)
- **Undercuts**: avoid or minimize; they require complex sliding cores that increase tooling cost and cycle time

### Materials Selection
- Mechanical properties: tensile strength, yield strength, hardness, impact resistance, fatigue life
- Thermal properties: melting point, glass transition temperature, thermal expansion, heat deflection temperature
- Chemical resistance: compatibility with expected environmental exposure (UV, moisture, solvents, oils)
- Aesthetic properties: colorability, surface finish achievable, transparency, texture, gloss level
- Cost and availability: raw material cost, processing cost, lead times, minimum order quantities

### Ergonomics and Human Factors
- **Anthropometric data**: use percentile ranges (5th to 95th) to accommodate diverse user populations
- **Grip and handle design**: consider hand size, grip type (power grip, precision grip), surface texture
- **Force requirements**: controls should require appropriate force — too little causes accidental activation, too much causes fatigue
- **Feedback**: tactile, auditory, and visual feedback confirm successful interaction with controls
- **Accessibility**: design for one-handed operation, limited dexterity, and varying strength levels

### Sustainability in Product Design
- **Design for disassembly**: use snap-fits instead of adhesives, standard fasteners, modular construction
- **Material reduction**: optimize structural geometry, remove unnecessary material, use lattice or honeycomb structures
- **Recycled and recyclable materials**: specify post-consumer recycled (PCR) content, avoid mixed-material assemblies
- **Lifecycle assessment (LCA)**: evaluate environmental impact from raw material extraction through end-of-life
- **Circular economy**: design for reuse, refurbishment, remanufacturing, and eventual recycling

## Practical Workflows

### 1. Design a Consumer Product from Concept to CAD
1. Sketch 10–15 concept variations exploring form, user interaction, and manufacturing approach
2. Select 2–3 concepts for refinement with rough ergonomic mockups (foam or cardboard) for physical evaluation
3. Build a parametric CAD model with proper draft angles, uniform wall thickness, and filleted edges ready for DFM review

### 2. Select a Material for an Injection-Molded Part
1. List functional requirements: operating temperature range, UV exposure, chemical contact, structural load, aesthetic finish
2. Compare candidate thermoplastics (ABS, polycarbonate, nylon, polypropylene) on mechanical properties and cost per part
3. Down-select based on mold flow characteristics, shrinkage rate, and availability in the desired color with UL rating

### 3. Perform an Ergonomic Grip Analysis
1. Identify the grip type (power grip for tools, precision grip for controls) and measure average hand anthropometry (5th–95th percentile)
2. Prototype handle profiles in three iterations with adjustable diameters and surface textures
3. Conduct user testing with 10+ participants measuring comfort, fatigue (time to muscle discomfort), and task completion rate

### 4. Prepare a Design for Manufacturing (DFM) Report
1. Review the CAD model for draft angles (minimum 1° per side), wall thickness uniformity, rib-to-wall ratios (50–60%), and radii
2. Identify undercuts, thin steel conditions, and non-standard parting lines that increase tooling complexity
3. Document recommended changes with before/after sections, estimated cost impact, and alternative manufacturing processes

### 5. Design a Sustainable Product for Disassembly
1. Choose a modular architecture with separable material groups (plastic housing, metal frame, electronic module)
2. Specify snap-fit connections instead of adhesives and standard fasteners (Phillips head) for easy disassembly
3. Mark all plastic parts with ISO recycling codes, eliminate co-molded materials, and provide a disassembly instruction card

## Best Practices

- Involve manufacturing engineers in the design process from concept stage; design-for-assembly input is cheapest when applied early.
- Prototype in iterative cycles: start with rapid low-fidelity models (foam, cardboard, clay) for form exploration, then move to functional prototypes for engineering validation.
- Specify tolerances realistically — tighter tolerances increase cost exponentially; only hold tight tolerances where functionally necessary.

## Manufacturing Process Selection Guide

| Process | Volume | Material | Tolerance | Relative Cost |
|---------|--------|----------|-----------|---------------|
| Injection Molding | High (10k+) | Thermoplastics | ±0.1mm | High tooling, low per-part |
| CNC Machining | Low-Medium | Metals, Plastics | ±0.05mm | Low tooling, medium per-part |
| 3D Printing (FDM) | Low (1–100) | Thermoplastics | ±0.5mm | Minimal tooling |
| Die Casting | High | Non-ferrous metals | ±0.2mm | High tooling, low per-part |
| Sheet Metal | Low-High | Steel, Aluminum | ±0.5mm | Low-medium tooling |

## Quality Checklist

- Draft angles are applied to all vertical surfaces (1–3° minimum)
- Wall thickness is uniform within ±25% of nominal
- All sharp internal corners have fillets (R ≥ 0.5mm)
- Material selection meets mechanical, thermal, and environmental requirements
- Anthropometric data covers 5th to 95th percentile users
- Prototype validation includes functional, ergonomic, and user testing
- DFM analysis completed with manufacturing partner or internal review
- Recyclability and end-of-life plan documented
