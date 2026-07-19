---
name: d3-charts
description: "Creates data visualizations using D3.js with scales, axes, SVG elements, transitions, and interactive charts."
license: MIT
compatibility: opencode
metadata:
  author: opencode
  version: "1.0.0"
  domain: frontend
  triggers: D3, D3.js, data visualization, chart, graph, SVG, scales, axes, bar chart, line chart, scatter plot, pie chart, force layout, map, geo
  role: specialist
  scope: implementation
  output-format: code
  related-skills: react-expert, vue-expert, frontend-ui-engineering, analysis-data-driven, tailwind-css
---

# D3.js / Data Visualization

D3.js visualization specialist — builds data-driven visualizations using D3 v7 with scales, axes, SVG rendering, transitions, interactions, and reusable chart components for web applications.

## When to Use This Skill

- Building custom charts and graphs that go beyond what charting libraries (Chart.js, Recharts, Victory) can accomplish
- Creating interactive data dashboards with linked views (brush-linked scatter + bar + line)
- Rendering geographic maps with projections, choropleth fills, and zoom/pan behavior
- Implementing dynamic, animated transitions between data states (enter, update, exit)
- Visualizing network graphs, trees, sunbursts, Sankey diagrams, or force-directed layouts

## Key Capabilities

- Create D3 scales (`scaleLinear`, `scaleBand`, `scaleOrdinal`, `scaleTime`, `scaleSequential`) and axes (`axisLeft`, `axisBottom`, `axisLabel`) with proper tick formatting
- Bind data to SVG elements using the general update pattern (enter, update, exit) with smooth transitions via `d3.transition`
- Build interactive features: tooltips, brush/zoom behaviors, click/hover handlers, and linked cross-filtering across multiple charts
- Render geographic visualizations using `d3-geo`, `d3-tile`, TopoJSON/GeoJSON, and map projections (`geoAlbersUsa`, `geoMercator`, `geoOrthographic`)
- Implement hierarchical (treemap, partition, pack), network (force-directed graph, chord), and flow (Sankey, chord) diagrams using D3 layouts

## Best Practices

- Use the general update pattern with keys (`data.join('g').attr('key', d => d.id)`) instead of clearing and re-rendering the entire SVG — preserves object constancy and enables smooth transitions
- Separate data transformation (using D3 array utilities) from rendering logic — keep `d3.csv`, `d3.json`, and data wrangling outside the chart component
- Abstract reusable chart components that accept a config object (width, height, margins, scales, color scheme) and expose methods for updating data without full re-renders
