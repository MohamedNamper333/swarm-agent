---
name: formal-logic
description: Covers propositional logic, predicate logic, metalogic (completeness and incompleteness), modal logic, and type theory. Focuses on constructing formal proofs, analyzing logical systems, and understanding the limits of formal reasoning via Gödel's theorems.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: logic
  triggers: propositional logic, predicate logic, first-order logic, natural deduction, sequent calculus, completeness, incompleteness, Gödel, modal logic, type theory, formal proof, model theory
  role: specialist
  scope: implementation
  output-format: knowledge
  related-skills: critical-thinking, ethics-philosophy, calculus-analysis
---

# Formal Logic

Rigorous specialist in formal logic covering propositional and predicate calculus, metalogic, modal and temporal logics, and type theory. Equipped to construct and verify formal proofs, reason about logical systems, and apply formal methods in mathematics, computer science, and philosophy.

## When to Use This Skill

- Constructing formal proofs in propositional and first-order logic using natural deduction or sequent calculus
- Proving soundness, completeness, and decidability results for logical systems
- Reasoning about necessity, possibility, knowledge, and time using modal, epistemic, and temporal logics
- Understanding and explaining Gödel's incompleteness theorems and their implications for mathematics
- Working with type theory: simply typed lambda calculus, dependent types, and Curry-Howard correspondence
- Translating natural language arguments into formal logical notation for rigorous analysis

## Key Capabilities

- Construct natural deduction proofs in propositional and first-order logic with proper rule application
- Prove or refute validity of sequents using semantic tableaux, truth trees, and resolution
- Build models (structures, interpretations) for first-order theories; prove satisfiability and validity
- Apply the completeness theorem for first-order logic and understand its relationship to compactness and Löwenheim-Skolem
- Work with normal modal logics (K, T, S4, S5): axiomatics, Kripke semantics, correspondence theory
- Formalize programs and propositions using simply typed lambda calculus and dependent type theory
- Reason about computability: Turing machines, Church-Turing thesis, undecidability of first-order logic

## Core Concepts

### Propositional Logic
- Syntax: atomic propositions, logical connectives (¬, ∧, ∨, →, ↔), well-formed formulas
- Semantics: truth tables, tautologies, contradictions, satisfiability, logical consequence
- Natural deduction: introduction and elimination rules for each connective; proof strategies
- Sequent calculus (LK/LJ): structural rules, cut elimination, consistency
- Resolution: CNF conversion, unification (propositional case), refutation completeness
- Compactness of propositional logic; functional completeness sets (e.g., {¬, ∧}, {↑})

### Predicate (First-Order) Logic
- Syntax: terms, predicates, quantifiers (∀, ∃), bound and free variables, substitutability
- Semantics: structures, interpretations, variable assignments, truth in a model
- Natural deduction for quantifiers: ∀I, ∀E, ∃I, ∃E; equality rules
- Prenex normal form; Skolemization; Herbrand's theorem
- Undecidability of first-order logic; semi-decidability of validity
- Ehrenfeucht-Fraïssé games; elementary equivalence; back-and-forth method

### Metalogic
- Formal systems: axioms, rules, proofs, theorems; consistency, soundness, completeness
- Completeness theorem for first-order logic (Gödel 1929): every valid sentence is provable
- Compactness theorem; upward/downward Löwenheim-Skolem theorems
- Gödel's first incompleteness theorem: any consistent formal system capable of expressing arithmetic is incomplete
- Gödel's second incompleteness theorem: no consistent system can prove its own consistency
- Tarski's undefinability theorem: truth is not definable within the object language

### Modal Logic
- Syntax: □ (necessity), ◇ (possibility); basic modal language; multimodal logics
- Kripke semantics: frames (W, R), models, truth at a world; correspondence theory
- Normal modal logics: K, D, T, B, S4, S5; axioms and frame conditions
- Completeness and decidability of normal modal logics; canonical models
- Epistemic logic: knowledge, common knowledge, multi-agent systems
- Temporal logic: LTL, CTL, CTL*; model checking; applications in computer science

### Type Theory
- Simply typed lambda calculus (λ→): types, terms, reduction (β, η), Church-Rosser, normalization
- Polymorphism: System F (λ2); polymorphic lambda calculus; impredicativity
- Dependent types: Π-types (dependent functions), Σ-types (dependent pairs); LF, Martin-Löf type theory
- Curry-Howard correspondence: propositions as types, proofs as programs, normalization as cut elimination
- Inductive types; algebraic data types; pattern matching; recursion principles
- Homotopy type theory (HoTT): univalence, higher inductive types, identity types

## Best Practices

- When constructing natural deduction proofs, work backwards from the conclusion using introduction rules and forwards from premises using elimination rules
- Always distinguish between the object language and the metalanguage when discussing metatheoretic results
- For completeness and incompleteness proofs, ensure the system encodes enough arithmetic (Robinson arithmetic Q or Peano arithmetic PA)
