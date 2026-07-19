---
name: critical-thinking
description: Covers argument analysis, formal and informal logical fallacies, cognitive biases, scientific reasoning, decision theory, Bayesian reasoning, and rhetoric. Emphasizes practical reasoning skills for debate, problem-solving, and evaluating claims in any domain.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: logic
  triggers: critical thinking, argument analysis, logical fallacies, cognitive biases, scientific reasoning, decision theory, Bayesian reasoning, Bayes theorem, rhetoric, debate, problem-solving, reasoning
  role: specialist
  scope: implementation
  output-format: knowledge
  related-skills: formal-logic, ethics-philosophy, analysis-data-driven
---

# Critical Thinking

Applied reasoning specialist focusing on argument reconstruction, fallacy identification, cognitive bias mitigation, Bayesian reasoning, decision theory, scientific methodology, and persuasive rhetoric. Provides practical tools for evaluating claims, making decisions under uncertainty, and constructing sound arguments.

## When to Use This Skill

- Analyzing the structure and validity of arguments encountered in articles, debates, or technical discussions
- Identifying formal and informal logical fallacies to evaluate the strength of reasoning
- Recognizing and mitigating cognitive biases in personal judgment, team decisions, or organizational processes
- Applying Bayesian reasoning to update beliefs in light of evidence and quantify uncertainty
- Making optimal decisions under uncertainty using decision theory: expected utility, game theory, risk analysis
- Evaluating scientific claims by assessing study design, statistical power, effect size, reproducibility, and p-hacking
- Constructing persuasive arguments using ethos, pathos, logos while maintaining intellectual honesty

## Key Capabilities

- Reconstruct arguments in standard form (premises + conclusion) with suppressed premises made explicit
- Diagnose formal fallacies (affirming the consequent, denying the antecedent, quantifier shift) and informal fallacies (ad hominem, straw man, false dilemma, slippery slope, etc.)
- Identify common cognitive biases: confirmation bias, anchoring, availability heuristic, Dunning-Kruger, sunk cost, survivorship bias, groupthink
- Perform Bayesian updates for hypothesis testing: prior, likelihood, posterior, and Bayes factor interpretation
- Use decision matrices, expected value calculations, and minimax regret for structured decision-making
- Apply scientific reasoning principles: falsification (Popper), paradigm shifts (Kuhn), research programs (Lakatos)
- Deconstruct rhetorical techniques: loaded language, weasel words, false equivalency, appeal to authority/nature/novelty

## Core Concepts

### Argument Analysis
- Standard form reconstruction; enthymemes; suppressed premises
- Deductive vs inductive vs abductive arguments; validity, soundness, strength, cogency
- Dialectical structure: thesis, antithesis, synthesis; pro/con analysis
- Argument mapping: premise-conclusion diagrams, convergent, linked, divergent structures
- Counterargument formulation: rebuttal, undercutting defeater, rebutting defeater
- Burden of proof; onus shifting; Russell's teapot; Hitchens's razor; Sagan's standard

### Logical Fallacies
- Formal fallacies: affirming the consequent, denying the antecedent, fallacy of four terms (quaternio terminorum), undistributed middle, illicit major/minor, quantifier shift
- Informal fallacies of relevance: ad hominem (abusive, circumstantial, tu quoque), ad populum, ad baculum, ad misericordiam, red herring
- Fallacies of ambiguity: equivocation, amphiboly, accent, composition, division
- Fallacies of presumption: begging the question, false dilemma, complex question, slippery slope, hasty generalization, faulty analogy
- Statistical fallacies: base rate fallacy, prosecutor's fallacy, gambler's fallacy, Simpson's paradox, survivorship bias

### Cognitive Biases
- Social biases: conformity bias, groupthink, authority bias, halo/horn effect
- Memory biases: availability heuristic, peak-end rule, recency effect, rosy retrospection
- Belief biases: confirmation bias, backfire effect, Dunning-Kruger effect, curse of knowledge
- Decision biases: anchoring, framing, sunk cost, status quo bias, ambiguity aversion, endowment effect
- Debiasing strategies: red teaming, pre-mortem, considering opposite, slowing down, checklist use, statistical thinking

### Scientific Reasoning
- Falsifiability (Popper); demarcation problem; ad hoc hypotheses
- Paradigms and scientific revolutions (Kuhn); normal science, anomaly, crisis, revolution
- Research programmes (Lakatos): hard core, protective belt, progressive vs degenerating shifts
- Study design: RCT, observational study, case-control, cohort; confounding variables
- Statistical reasoning: p-values, confidence intervals, effect size, statistical power, multiple comparisons, p-hacking, HARKing, publication bias
- Reproducibility crisis: preregistration, replication studies, registered reports, meta-analysis

### Bayesian Reasoning
- Bayes' theorem: P(H|E) = P(E|H)P(H) / P(E)
- Prior, likelihood, posterior, evidence (marginal likelihood)
- Bayes factor: quantifying strength of evidence; Jeffreys scale
- Bayesian updating for sequential evidence; conjugate priors
- Bayesian vs frequentist: interpretations of probability, confidence intervals vs credible intervals
- Common Bayesian fallacies: base rate neglect, ignoring priors, overconfidence in likelihoods

### Decision Theory
- Expected utility theory: EU(A) = Σ P(O_i|A) × U(O_i)
- Rational choice; axioms of von Neumann-Morgenstern utility; Allais and Ellsberg paradoxes
- Game theory: Nash equilibrium, prisoner's dilemma, coordination games, signaling
- Decision under uncertainty: maximax, maximin, minimax regret, Laplace criterion
- Prospect theory: loss aversion, reference dependence, diminishing sensitivity, framing effects
- Multi-criteria decision analysis: weighted scoring, AHP, TOPSIS, cost-benefit analysis

### Rhetoric
- Aristotelian appeals: ethos (credibility), pathos (emotion), logos (reason)
- Modes of persuasion; rhetorical devices: metaphor, analogy, rhetorical question, tricolon, anaphora
- Argumentative strategy: stasis theory, stock issues (policy debate), primacy/recency
- Propaganda techniques: glittering generality, transfer, testimonial, plain folks, card stacking, bandwagon
- Intellectual virtues: charity principle, steelmanning, open-mindedness, intellectual humility, fallibilism

## Best Practices

- Before critiquing an argument, steelman it — reconstruct the strongest version the opponent has or could offer
- When updating beliefs, write down explicit prior probabilities and likelihoods rather than relying on intuition
- Use the Bayesian Occam's razor: simpler explanations that make more precise predictions receive a higher posterior, all else being equal
