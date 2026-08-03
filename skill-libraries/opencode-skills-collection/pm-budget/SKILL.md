---
name: pm-budget
description: Manages project budget, cost estimation, financial tracking, and ROI analysis. Use when planning budget, tracking costs, forecasting spend, or calculating project ROI.
license: MIT
compatibility: opencode
metadata:
  author: https://github.com/opencode
  version: "1.0.0"
  domain: project-management
  triggers:
    - "budget"
    - "cost estimation"
    - "financial tracking"
    - "ROI analysis"
    - "forecast spend"
    - "EVM"
    - "earned value"
  role: specialist
  scope: implementation
  output-format: code
---

# Budget & Cost Management

## Budget Planning
- **Bottom-up**: estimate every work package, sum with contingency
- **Top-down**: allocate from total pool, prioritize by value
- **Parametric**: cost = unit rate × quantity (e.g., $150/hr × 500 hrs)
- **Three-point**: (optimistic + 4×likely + pessimistic) / 6

## Cost Breakdown Structure
- Labor (internal + external), software/tools, infrastructure, licenses
- Travel, training, contingency (10-20%), management reserve

## Tracking & Variance
- **Earned Value Management (EVM)**:
  - Planned Value (PV): budgeted cost of scheduled work
  - Earned Value (EV): budgeted cost of completed work
  - Actual Cost (AC): actual cost incurred
  - Cost Variance (CV) = EV - AC (negative = over budget)
  - Schedule Variance (SV) = EV - PV (negative = behind)
  - CPI = EV/AC (< 1 = over budget), SPI = EV/PV (< 1 = behind)

## Forecasting
- Estimate at Completion (EAC) = AC + (BAC - EV) / CPI
- Variance at Completion (VAC) = BAC - EAC
- To-Complete Performance Index (TCPI) = (BAC - EV) / (BAC - AC)

## Financial Reports
- Monthly burn rate, remaining budget, % spent vs % complete
- Variance analysis with explanation for each line item
- Forecast vs actual trend charts

## When to Use This Skill

- You need to produce a detailed project budget with defensible cost estimates for approval or funding requests
- You are mid-project and need to track actual spend against plan, calculate variance, and forecast the final cost
- You want to evaluate the financial viability of a project through ROI, payback period, or net present value analysis
- You need to apply Earned Value Management to get an objective, metric-driven view of cost and schedule health
- You are preparing monthly or weekly financial status reports for stakeholders, sponsors, or governance boards

## Key Capabilities

- Produces bottom-up, top-down, parametric, and three-point estimates matched to the level of certainty available
- Builds a complete Cost Breakdown Structure covering labor, tools, infrastructure, licenses, travel, and contingency reserves
- Implements full Earned Value Management (PV, EV, AC, CV, SV, CPI, SPI) for objective performance measurement
- Generates EAC, VAC, and TCPI forecasts to answer "how much more will this cost?" and "can we still hit the target?"
- Structures financial reports with burn rate, remaining budget, variance explanations, and forecast vs actual trends

## Best Practices

- Always include a contingency reserve (10-20%) and a separate management reserve — the two serve different purposes and should not be conflated
- Re-forecast at every major milestone or when actual variance exceeds ±10%; stale budgets erode trust in the numbers
- Track cost and schedule together — a project under budget but far behind schedule is not a healthy project
