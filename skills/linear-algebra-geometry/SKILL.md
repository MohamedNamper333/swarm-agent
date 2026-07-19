---
name: linear-algebra-geometry
description: Covers linear algebra (vectors, matrices, eigenvalues, linear transformations), analytic geometry, differential geometry, and topology. Emphasizes applications in machine learning, computer graphics, physics, and data science.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: mathematics
  triggers: linear algebra, vectors, matrices, eigenvalues, eigenvectors, SVD, linear transformations, analytic geometry, differential geometry, topology, manifolds, tensors
  role: specialist
  scope: implementation
  output-format: knowledge
  related-skills: calculus-analysis, classical-physics, modern-physics
---

# Linear Algebra & Geometry

Specialist in linear algebra, analytic and differential geometry, and topology — the mathematical backbone of modern computing, scientific computing, machine learning, graphics, and theoretical physics. Bridges abstract algebraic structures with concrete computational applications.

## When to Use This Skill

- Solving systems of linear equations using Gaussian elimination, LU/QR/SVD decompositions
- Computing eigenvalues and eigenvectors for matrix diagonalization, PCA, and spectral analysis
- Applying linear transformations in 2D/3D graphics: rotation, scaling, reflection, shear, projection
- Working with vector spaces, subspaces, bases, dimension, and orthogonality in inner product spaces
- Analyzing data using singular value decomposition (SVD), eigenvalues, and low-rank approximations
- Modeling curves and surfaces with differential geometry for physics, graphics, or robotics

## Key Capabilities

- Perform matrix factorizations: LU, QR, Cholesky, SVD, eigendecomposition with computational efficiency analysis
- Construct and manipulate coordinate systems, affine transformations, and projective geometry for graphics and robotics
- Derive properties of linear operators: kernel, image, rank-nullity theorem, change of basis
- Compute curvature, geodesics, and connection forms on Riemannian manifolds
- Apply topological concepts: open/closed sets, compactness, connectedness, homotopy, homology
- Use tensor algebra for applications in continuum mechanics, general relativity, and deep learning
- Implement numerical linear algebra algorithms with attention to stability, conditioning, and complexity

## Core Concepts

### Linear Algebra
- Vector spaces: axioms, subspaces, linear independence, span, basis, dimension
- Linear transformations: kernel, image, rank-nullity theorem, matrix representation, change of basis
- Systems of linear equations: Gaussian elimination, row echelon form, rank, consistency, nullspace
- Determinants: computation, properties, geometric interpretation (volume), Cramer's rule
- Inner product spaces: dot product, norm, orthogonality, Gram-Schmidt, orthogonal complements
- Eigenvalues and eigenvectors: characteristic polynomial, algebraic/geometric multiplicity, diagonalization
- Matrix decompositions: LU, QR, Cholesky, SVD, polar decomposition, Jordan canonical form
- Applications: PCA, least squares, Markov chains, PageRank, graph Laplacians, linear programming

### Analytic Geometry
- Cartesian coordinate systems; lines, planes, distance formulas
- Conic sections: ellipse, parabola, hyperbola — equations, foci, eccentricity
- Quadratic surfaces: ellipsoid, paraboloid, hyperboloid — classification via quadratic forms
- Polar, cylindrical, spherical coordinate systems; coordinate transformations
- Affine geometry: affine combinations, barycentric coordinates, affine maps
- Projective geometry: homogeneous coordinates, projective transformations, cross-ratio

### Differential Geometry
- Curves: parameterization, arc length, curvature, torsion, Frenet-Serret frame
- Surfaces: first and second fundamental forms, Gaussian curvature, mean curvature
- Manifolds: charts, atlases, tangent spaces, vector fields, differential forms
- Riemannian geometry: metric tensor, Levi-Civita connection, geodesics, curvature tensor
- Lie groups and Lie algebras: SO(3), SE(3), exponential map, applications to robotics
- Applications: general relativity (spacetime curvature), computer graphics (mesh processing), ML (manifold learning)

### Topology
- Point-set topology: topological spaces, open/closed sets, neighborhood, basis, product/quotient topologies
- Continuity in topological spaces; homeomorphisms; topological invariants
- Compactness: Heine-Borel, sequential compactness, compactness in metric spaces
- Connectedness: path-connected, simply connected, components
- Homotopy: homotopy equivalence, fundamental group, covering spaces
- Algebraic topology: homology groups (simplicial, singular), Euler characteristic, Mayer-Vietoris sequence
- Applications: data topology (persistent homology), network topology, configuration spaces in robotics

## Best Practices

- Choose basis sets that diagonalize or simplify the problem before performing heavy computation
- Check condition number of matrices before solving linear systems numerically; use SVD for ill-conditioned problems
- When applying spectral theorems, verify the operator is self-adjoint (symmetric/Hermitian) first
