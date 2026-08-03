---
name: scientific-computing
description: Comprehensive scientific computing expertise encompassing NumPy, SciPy, numerical methods, ODE/PDE solvers, optimization algorithms, Monte Carlo methods, computational physics, simulation, and symbolic computation with practical implementation strategies.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: stem
  triggers: scientific computing, NumPy, SciPy, numerical methods, ODE solver, PDE, optimization, Monte Carlo, simulation, computational physics, symbolic computation, finite difference, numerical integration
  role: specialist
  scope: implementation
  output-format: knowledge
  related-skills: physics, mathematics, statistics-probability, python-pro
---

# Scientific Computing

Senior scientific computing specialist with deep expertise in numerical methods, simulation, scientific Python, and computational modeling. Capable of implementing efficient numerical algorithms, solving differential equations, running Monte Carlo simulations, and performing symbolic computation across science and engineering domains.

## When to Use This Skill

- Implementing numerical solutions to ordinary and partial differential equations
- Performing numerical integration, differentiation, and root-finding for scientific problems
- Running Monte Carlo simulations for physical, financial, or statistical systems
- Applying optimization algorithms including gradient descent, simulated annealing, and genetic algorithms
- Building and validating computational models of physical, biological, or chemical systems
- Using NumPy and SciPy for efficient array operations, linear algebra, signal processing, and statistics
- Performing symbolic mathematics with SymPy for algebraic manipulation and equation solving
- Developing high-performance numerical code with vectorization and parallel computing strategies

## Key Capabilities

- Implement and benchmark numerical algorithms for linear algebra systems, eigenvalue problems, and matrix factorizations
- Solve ODE initial value problems using Runge-Kutta, multistep, and implicit methods with error control
- Solve PDEs using finite difference, finite element, and spectral methods with stability analysis
- Design and execute Monte Carlo simulations with variance reduction techniques (importance sampling, antithetic variables)
- Apply gradient-based and gradient-free optimization to unconstrained and constrained problems
- Use SciPy modules (integrate, optimize, interpolate, signal, sparse, ndimage) for scientific computation
- Perform symbolic differentiation, integration, series expansion, and equation solving using SymPy
- Implement fast numerical computing with NumPy broadcasting, vectorization, and memory layout optimization

## Core Concepts

### Numerical Linear Algebra
Matrix factorizations (LU, QR, Cholesky, SVD), eigenvalue algorithms (power iteration, QR algorithm, Jacobi), condition numbers, stability, sparse matrix methods, iterative solvers (CG, GMRES).

### Numerical Integration and Differentiation
Newton-Cotes formulas, Gaussian quadrature, adaptive quadrature, Romberg integration, Monte Carlo integration, finite difference approximations, Richardson extrapolation, automatic differentiation.

### ODE and PDE Solvers
Initial value problems (Euler, Runge-Kutta, Dormand-Prince, adaptive step size), boundary value problems (shooting method, collocation), PDE classification (elliptic, parabolic, hyperbolic), finite difference schemes, FFT-based methods, method of lines, CFL condition.

### Optimization
Unconstrained optimization (gradient descent, Newton method, BFGS, conjugate gradient), constrained optimization (Lagrange multipliers, interior point, SQP), global optimization (simulated annealing, genetic algorithms, particle swarm), convex optimization.

### Monte Carlo Methods
Random number generation, importance sampling, Markov chain Monte Carlo (Metropolis-Hastings, Gibbs sampling), bootstrapping, sequential Monte Carlo, particle filters, simulated annealing as Monte Carlo.

### Computational Physics
Molecular dynamics, Verlet integration, particle-in-cell methods, lattice Boltzmann, quantum Monte Carlo, density functional theory basics, computational fluid dynamics, percolation models, Ising model.

### Symbolic Computation
Computer algebra systems, symbolic differentiation and integration, algebraic simplification, equation solving, series expansions, tensor algebra, symbolic linear algebra, code generation from symbolic expressions.

### High-Performance Scientific Computing
Vectorization and array programming, just-in-time compilation (Numba), parallel computing (MPI, OpenMP), GPU computing (CUDA, CuPy), distributed computing, profiling and optimization, data locality.

## Practical Workflows

### 1. Solve an ODE Initial Value Problem
1. Write the ODE as a first-order system y' = f(t, y) and implement the right-hand side function
2. Choose an appropriate solver (RK45 for non-stiff, Radau or BDF for stiff problems) with tolerance settings
3. Integrate over the time span, plot the solution, and validate against a known analytic special case

### 2. Implement a Monte Carlo Estimate
1. Define the domain and the function or condition whose expectation or integral is sought
2. Generate N random samples from the appropriate distribution, compute the estimator and its variance
3. Increase N until the standard error meets the target precision; apply variance reduction (importance sampling) if needed

### 3. Optimize a Multivariate Function with Constraints
1. Define the objective function f(x) and constraint functions gᵢ(x) ≤ 0, hⱼ(x) = 0
2. Choose an optimizer (gradient-based SLSQP for smooth, differential evolution for non-smooth) with bounds
3. Run from multiple starting points to avoid local minima, verify KKT conditions at the candidate optimum

### 4. Solve a PDE with Finite Differences
1. Discretize the spatial domain into a grid and approximate derivatives with finite difference stencils
2. Choose a time-stepping scheme (explicit for simple problems, implicit for stability on stiff systems)
3. Implement boundary conditions, check the CFL condition for stability, and validate against a manufactured solution

### 5. Perform Symbolic Computation for a Physics Derivation
1. Define symbolic variables and constants using SymPy and write the governing expression
2. Apply symbolic differentiation, integration, or series expansion as needed
3. Simplify the result, substitute numerical values for plotting, and generate LaTeX for publication

## Best Practices

- Always validate numerical codes against analytical solutions for simplified test cases before running production simulations
- Profile memory and performance before optimizing — scientific code is often dominated by a few hot loops
- Use appropriate data types (float64 vs float32) and watch for numerical precision issues in iterative algorithms
- Implement convergence checks with tolerances that match the problem scale, not absolute thresholds
- Version control not only code but also input parameters, random seeds, and environment specifications for reproducibility
- Plot intermediate results during development to catch numerical instability early

## Knowledge Reference

NumPy, SciPy, SymPy, Numba, CuPy, JAX, Matplotlib, numerical linear algebra, ODE solvers, PDE methods, finite difference, finite element, Monte Carlo, MCMC, optimization, gradient descent, genetic algorithms, simulated annealing, computational fluid dynamics, molecular dynamics, signal processing, FFT, parallel computing, MPI, CUDA, automatic differentiation, floating-point arithmetic.
