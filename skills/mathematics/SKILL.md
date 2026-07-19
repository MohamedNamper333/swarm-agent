---
name: mathematics
description: Complete mathematics mastery covering algebra, calculus, linear algebra, geometry, topology, number theory, discrete mathematics, and real/complex analysis. Provides rigorous proof techniques, problem-solving strategies, and cross-domain mathematical reasoning.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: stem
  triggers: mathematics, algebra, calculus, linear algebra, geometry, topology, number theory, proof, analysis, discrete math, trig, function, equation, theorem
  role: specialist
  scope: implementation
  output-format: knowledge
  related-skills: physics, scientific-computing, statistics-probability, logic
---

# Mathematics

Senior mathematics specialist with comprehensive expertise from foundational algebra to advanced analysis, topology, and number theory. Capable of constructing rigorous proofs, developing mathematical models, and solving problems across all pure and applied mathematical domains.

## When to Use This Skill

- Solving algebraic equations, systems, and abstract algebraic structures
- Performing differential and integral calculus including multivariable and vector calculus
- Applying linear algebra for transformations, eigenvalues, and matrix decompositions
- Constructing rigorous mathematical proofs using direct, contrapositive, contradiction, and induction methods
- Solving problems in number theory including congruences, Diophantine equations, and prime distribution
- Working with discrete mathematics including combinatorics, graph theory, and recurrence relations
- Analyzing real and complex functions with rigorous epsilon-delta techniques
- Applying topological concepts including continuity, compactness, connectedness, and homotopy

## Key Capabilities

- Solve problems across elementary algebra, abstract algebra (groups, rings, fields, modules), and category theory
- Perform differentiation, integration, series expansions, and differential equation solving with rigor
- Execute linear algebra operations: matrix factorizations, vector spaces, linear transformations, spectral theory
- Construct proofs by induction, contradiction, contrapositive, direct reasoning, and combinatorial arguments
- Apply real analysis techniques: limits, continuity, differentiation, Riemann/Lebesgue integration, sequences, series
- Use complex analysis tools: analytic functions, contour integration, residues, conformal mappings
- Solve combinatorial and graph theory problems including counting, optimization, and network flows
- Employ number theoretic methods: modular arithmetic, primitive roots, quadratic reciprocity, analytic number theory

## Core Concepts

### Algebra and Abstract Algebra
Elementary algebra, polynomials, complex numbers, groups (permutation, cyclic, dihedral), rings, ideals, fields, Galois theory, vector spaces, modules, category theory, functors, natural transformations.

### Calculus and Analysis
Limits, continuity, differentiation, Riemann integration, Fundamental Theorem of Calculus, sequences, series, power series, Taylor expansions, multivariable calculus, gradient, divergence, curl, implicit function theorem.

### Linear Algebra
Matrices, determinants, Gaussian elimination, vector spaces, linear transformations, inner products, orthogonality, eigenvalues and eigenvectors, diagonalization, singular value decomposition, Jordan canonical form.

### Geometry and Topology
Euclidean geometry, non-Euclidean geometry, differential geometry, manifolds, tensors, point-set topology, compactness, connectedness, homotopy theory, fundamental group, covering spaces, simplicial complexes.

### Number Theory
Prime numbers, modular arithmetic, Fermat's little theorem, Euler's theorem, Chinese remainder theorem, quadratic reciprocity, Diophantine equations, continued fractions, analytic number theory, zeta function.

### Discrete Mathematics
Combinatorics, permutations, combinations, generating functions, graph theory, trees, matchings, network flow, Boolean algebra, recurrence relations, finite automata, computational complexity.

### Real and Complex Analysis
Metric spaces, normed spaces, Banach spaces, Hilbert spaces, Lebesgue measure and integration, analytic functions, Cauchy-Riemann equations, Cauchy integral formula, Laurent series, residue theorem.

## Practical Workflows

### 1. Solve a System of Linear Equations
1. Write the system in matrix form Ax = b, identify dimensions and check consistency
2. Reduce to row-echelon form via Gaussian elimination, tracking rank and nullspace
3. Back-substitute to find solution set, verify by computing Ax and comparing to b

### 2. Compute a Definite Integral
1. Identify integrand type (polynomial, trigonometric, rational, improper) and check continuity on the interval
2. Apply the fundamental theorem, substitution, integration by parts, or contour integration as appropriate
3. Evaluate analytically, verify by numerical approximation (e.g., Simpson's rule), check endpoint behavior

### 3. Find Eigenvalues and Eigenvectors
1. Form the characteristic polynomial det(A - λI) = 0 and compute eigenvalues
2. For each eigenvalue, solve (A - λI)v = 0 to find the eigenvector basis
3. Check diagonalization: if eigenvectors span the space, form P and D and verify A = PDP⁻¹

### 4. Prove a Statement by Induction
1. State the proposition P(n) explicitly and verify the base case (usually n = 1 or n = 0)
2. Assume P(k) holds for arbitrary k ≥ base, derive P(k+1) from P(k) using algebraic or logical manipulation
3. Conclude by induction that P(n) holds for all n, and test a non-trivial instance numerically

### 5. Perform a Least-Squares Regression
1. Set up the overdetermined system Ax ≈ b with more equations than unknowns
2. Solve the normal equations AᵀAx = Aᵀb or use QR decomposition for numerical stability
3. Compute the residual norm and R² to assess goodness of fit, inspect the residual plot for patterns

## Best Practices

- Clearly state assumptions, givens, and what is to be proved before starting any problem
- Test boundary cases and degenerate conditions to validate conjectures or solutions
- Choose the simplest proof technique first — direct proof before contradiction, induction before advanced methods
- Verify solutions by plugging back into original equations or checking against known limiting cases
- Maintain rigorous variable definitions and avoid ambiguous notation across derivations

## Knowledge Reference

Algebra, calculus, linear algebra, real analysis, complex analysis, functional analysis, topology, differential geometry, number theory, combinatorics, graph theory, category theory, logic, set theory, measure theory, probability theory, partial differential equations, numerical analysis, optimization theory.
