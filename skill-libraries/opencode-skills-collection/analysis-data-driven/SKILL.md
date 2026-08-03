---
name: analysis-data-driven
description: "Use for data analysis, statistics, data visualization, and evidence-based decision making. Activate when the user asks about data, metrics, statistics, dashboards, or analytics."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: analysis
  triggers: data analysis, statistics, metrics, dashboard, analytics, A/B testing, cohort, KPI, regression, hypothesis testing, data viz, data-driven, evidence-based, measurement
  role: specialist
  scope: implementation
  output-format: report
  related-skills: analysis-systems, business-analysis, d3-charts, pm-risk, monitoring-expert, feature-forge
---

# Data-Driven Analysis

Data-driven analysis specialist — applies statistical methods, data visualization principles, and evidence-based reasoning to transform raw data into actionable business and product decisions.

## When to Use This Skill

- Analyzing product metrics, user behavior, or business KPIs to inform strategic decisions
- Designing and interpreting A/B tests or experiments — sample size calculation, statistical significance, effect size
- Building dashboards and reports that surface meaningful trends, anomalies, and correlations
- Investigating a sudden change in a key metric (spike, drop, flatline) using exploratory data analysis
- Evaluating the impact of a feature release, pricing change, or marketing campaign using before/after or cohort comparison

## Key Capabilities

- Apply descriptive statistics (mean, median, mode, standard deviation, IQR, percentiles) and explore distributions (histogram, boxplot, Q-Q plot) to understand data shape and detect outliers
- Perform inferential statistics — confidence intervals, p-values, t-tests, chi-square, ANOVA, and non-parametric alternatives — with proper assumptions checking
- Design and analyze controlled experiments — define hypotheses, calculate minimum sample size, run power analysis, detect Simpson's paradox, and evaluate practical significance vs statistical significance
- Build data pipelines for analysis: collect from APIs/CSVs/databases, clean missing values and outliers, transform and aggregate, then visualize using line/bar/scatter/heatmap/cohort charts
- Identify and communicate causal vs correlational relationships, survivorship bias, selection bias, confounders, and regression to the mean

## Best Practices

- Always define the question and success metric before looking at the data — post-hoc analysis inflates false discovery rates and leads to confirmation bias
- Never truncate the y-axis on bar/line charts — it exaggerates differences and misleads viewers; start at zero for bar charts
- Use cohort analysis over simple aggregate averages to isolate time-based changes in user behavior and distinguish acquisition effects from product effects
