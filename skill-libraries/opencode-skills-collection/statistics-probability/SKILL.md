---
name: statistics-probability
description: Comprehensive statistics and probability expertise covering descriptive statistics, inferential statistics, probability theory, Bayesian inference, hypothesis testing, regression analysis, and experimental design. Specializes in rigorous data analysis and statistical reasoning.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: stem
  triggers: statistics, probability, hypothesis test, regression, Bayesian, distribution, confidence interval, p-value, ANOVA, correlation, chi-square, t-test, A/B testing, inference, data analysis
  role: specialist
  scope: implementation
  output-format: knowledge
  related-skills: mathematics, scientific-computing, python-pro, pandas-pro
---

# Statistics & Probability

Senior statistics and probability specialist with deep expertise in descriptive and inferential methods, probability theory, Bayesian analysis, experimental design, and statistical modeling. Capable of designing experiments, analyzing data, drawing valid inferences, and communicating statistical findings with rigor.

## When to Use This Skill

- Designing experiments and observational studies with proper controls, randomization, and sample size determination
- Performing hypothesis tests (t-tests, chi-square, ANOVA, non-parametric tests) with appropriate assumptions
- Building and interpreting regression models (linear, logistic, multiple, hierarchical)
- Applying Bayesian inference including prior specification, posterior computation, and model comparison
- Computing and interpreting probability distributions, expectations, and stochastic processes
- Analyzing data with descriptive statistics, visualizations, and exploratory data analysis
- Calculating confidence intervals, effect sizes, and power analysis for study design
- Evaluating causal claims using methods such as randomized experiments, instrumental variables, or difference-in-differences

## Key Capabilities

- Compute and interpret descriptive statistics: mean, median, variance, skewness, kurtosis, quantiles
- Apply probability theory: combinatorics, axioms, conditional probability, Bayes' theorem, random variables
- Work with discrete and continuous probability distributions (binomial, Poisson, normal, exponential, gamma, beta)
- Conduct hypothesis tests with proper null and alternative specifications, test selection, and assumption checking
- Build and validate regression models with diagnostics for multicollinearity, heteroscedasticity, and influential points
- Apply Bayesian methods: conjugate priors, MCMC, credible intervals, Bayes factors, hierarchical models
- Perform ANOVA (one-way, two-way, repeated measures, mixed effects) with post-hoc comparisons
- Design experiments including randomized controlled trials, factorial designs, and sequential analysis

## Core Concepts

### Probability Theory
Sample space, events, axioms of probability, conditional probability, independence, Bayes' theorem, random variables, probability mass functions, probability density functions, cumulative distribution functions, expectation, variance, covariance, moment generating functions, weak and strong laws of large numbers, central limit theorem.

### Probability Distributions
Discrete: Bernoulli, binomial, geometric, Poisson, hypergeometric, negative binomial. Continuous: uniform, normal, exponential, gamma, beta, chi-square, t, F, log-normal, Weibull, Dirichlet. Multivariate distributions, copulas.

### Descriptive Statistics
Measures of central tendency (mean, median, mode), dispersion (variance, standard deviation, IQR), shape (skewness, kurtosis), exploratory data analysis, box plots, histograms, Q-Q plots, stem-and-leaf displays, correlation matrices.

### Inferential Statistics
Point estimation, bias and variance of estimators, maximum likelihood estimation, method of moments, confidence intervals, bootstrapping, sufficiency, Rao-Blackwell theorem, Cramér-Rao lower bound.

### Hypothesis Testing
Null and alternative hypotheses, Type I and Type II errors, significance level, p-values, power analysis, one-sample and two-sample t-tests, paired tests, chi-square tests (goodness of fit, independence), ANOVA, F-tests, non-parametric tests (Mann-Whitney, Wilcoxon, Kruskal-Wallis, Kolmogorov-Smirnov).

### Regression and Linear Models
Simple linear regression, multiple regression, polynomial regression, interaction terms, ANOVA as linear model, diagnostics (residuals, leverage, Cook's distance), variable selection (stepwise, LASSO, ridge), logistic regression, generalized linear models, mixed models.

### Bayesian Statistics
Prior distributions, likelihood, posterior distributions, conjugate priors, Bayesian computation (grid approximation, MCMC, Stan, PyMC), credible intervals, Bayes factors, model comparison, hierarchical Bayesian models, empirical Bayes.

### Experimental Design
Randomization, blocking, factorial designs, fractional factorial designs, response surface methodology, sample size determination, power analysis, sequential analysis, A/B testing, multi-armed bandits, causal inference (potential outcomes, propensity scores, instrumental variables, regression discontinuity).

## Practical Workflows

### 1. Conduct an A/B Test Analysis
1. Formulate the null hypothesis (no difference between variants) and alternative, set significance level α = 0.05
2. Compute the sample mean and standard deviation for each group, run the appropriate test (two-sample t-test or chi-square)
3. Report p-value, effect size (Cohen's d or risk ratio), and confidence interval; interpret practical significance

### 2. Build a Linear Regression Model
1. Examine scatter plots and the correlation matrix to assess linear relationships and multicollinearity
2. Fit the model using ordinary least squares, check residual diagnostics (normality, homoscedasticity, independence)
3. Iterate by transforming variables or adding interactions, compare models with adjusted R² and AIC

### 3. Perform a Bayesian Analysis
1. Specify the prior distribution based on domain knowledge or weakly informative defaults
2. Define the likelihood function from the data-generating process and compute the posterior (analytically or via MCMC)
3. Summarize the posterior with credible intervals, compute the Bayes factor for model comparison, check sensitivity to the prior

### 4. Determine Sample Size for a Study
1. Specify the desired power (typically 0.80), significance level (0.05), and minimum detectable effect size
2. Choose the appropriate test family and run power analysis using analytical formulas or simulation
3. Adjust for expected attrition, clustering, or multiple comparisons; document all assumptions

### 5. Detect Outliers in a Dataset
1. Visualize data with box plots, histograms, and Q-Q plots to identify extreme observations
2. Apply statistical tests (Grubbs' test, IQR rule, Mahalanobis distance) with transparent criteria
3. Investigate each candidate outlier for data entry errors, measurement issues, or genuine rare events before deciding on exclusion

## Best Practices

- Always visualize data before applying any statistical test — distribution, outliers, and patterns should inform method selection
- Check assumptions of every statistical procedure (normality, independence, homogeneity of variance) and use robust alternatives when violated
- Pre-register analyses and distinguish confirmatory from exploratory work to avoid p-hacking
- Report effect sizes and confidence intervals alongside p-values, not p-values alone
- Use Bayesian methods when prior information is available or when quantifying evidence for the null hypothesis is needed
- Adjust for multiple comparisons when conducting many hypothesis tests simultaneously
- Document every data exclusion, transformation, and analysis decision for reproducibility

## Knowledge Reference

Probability theory, descriptive statistics, inferential statistics, hypothesis testing, regression, ANOVA, Bayesian statistics, MCMC, experimental design, causal inference, time series analysis, survival analysis, factor analysis, principal component analysis, clustering, classification, power analysis, effect size, meta-analysis, non-parametric statistics, multivariate statistics, stochastic processes, Markov chains.
