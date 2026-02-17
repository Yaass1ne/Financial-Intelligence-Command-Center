# FINCENTER Dashboard

High-impact React dashboard for the Financial Intelligence Command Center (FINCENTER) platform.

## Overview

A professional, modern financial dashboard built with React, TypeScript, Tailwind CSS, and Recharts. Features 5 comprehensive pages for financial management and analysis.

## Technologies

- **React 18** - Modern UI framework
- **TypeScript** - Type-safe development
- **Vite** - Fast build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **React Router** - Client-side routing
- **Recharts** - Interactive data visualizations
- **Lucide React** - Beautiful icon library

## Pages

### 1. Budget Augmented Dashboard (`/`)
- Real-time budget variance tracking
- Summary cards for total budget, actual spend, variance, and departments over budget
- Interactive charts:
  - Budget vs Actual bar chart by department
  - Budget distribution pie chart
- Detailed department budget table with variance analysis
- Color-coded status indicators (over/under budget)

### 2. Contracts & Clauses Management (`/contracts`)
- Track expiring contracts (30/60/90 day filters)
- Search functionality by vendor or contract ID
- Summary metrics:
  - Total contracts expiring
  - Critical contracts (≤30 days)
  - Warning contracts (31-60 days)
  - Total value at risk
- Urgency-based color coding (critical/warning/normal)
- Contract details: expiration date, annual value, auto-renewal status

### 3. Invoices & Treasury Management (`/invoices`)
- Overdue invoice tracking
- Filter by overdue period (all, 30+, 60+, 90+ days)
- Key metrics:
  - Total overdue invoices
  - Outstanding balance
  - Critical invoices (>60 days overdue)
  - Average days overdue
- Comprehensive invoice table with urgency levels
- Color-coded urgency indicators (critical/high/medium/low)

### 4. Alerts & Recommendations (`/alerts`)
- AI-powered insights and actionable recommendations
- Multiple alert types: critical, warning, info, success
- Categories: Budget, Contract, Invoice, Optimization
- Each alert includes:
  - Description of the issue
  - Specific recommendation
  - Impact assessment
  - Timestamp
- Summary cards for total alerts, critical, warnings, and opportunities

### 5. Simulations & Scenarios (`/simulations`)
- Interactive financial modeling
- Adjustable parameters:
  - Budget cut percentage (0-30%)
  - Revenue growth rate (0-20%)
  - Inflation rate (0-10%)
- Real-time calculations and visualizations
- 12-month projection chart with multiple scenarios:
  - Baseline
  - With budget cuts
  - With inflation
  - Optimized
- Quick scenario presets:
  - Conservative Growth
  - Aggressive Expansion
  - Crisis Mode
- Dynamic insights based on selected parameters

## API Integration

The dashboard connects to the FINCENTER API at `http://localhost:8080/api`

**Endpoints used:**
- `/budgets/summary?year=2024` - Budget variance data
- `/contracts/expiring?days={days}` - Expiring contracts
- `/invoices/overdue?days={days}` - Overdue invoices

## Getting Started

### Prerequisites
- Node.js 18+ installed
- FINCENTER API server running on port 8080

### Installation

```bash
cd dashboard
npm install
```

### Development

```bash
npm run dev
```

Dashboard will be available at: **http://localhost:5174**

### Build for Production

```bash
npm run build
npm run preview
```

## Features

✅ **Responsive Design** - Works on desktop, tablet, and mobile
✅ **Modern UI** - Clean, professional interface with Tailwind CSS
✅ **Interactive Charts** - Recharts for beautiful data visualizations
✅ **Real-time Data** - Connected to live API endpoints
✅ **Type Safety** - Full TypeScript coverage
✅ **Fast Performance** - Vite for instant HMR
✅ **Intuitive Navigation** - React Router with clear page structure
✅ **Color-coded Alerts** - Visual indicators for urgency levels
✅ **Interactive Simulations** - Real-time financial modeling

## Project Structure

```
dashboard/
├── src/
│   ├── components/
│   │   ├── Layout.tsx           # Main layout with navigation
│   │   └── ui/
│   │       └── Card.tsx          # Reusable card components
│   ├── pages/
│   │   ├── BudgetDashboard.tsx       # Page 1: Budget variance
│   │   ├── ContractsDashboard.tsx    # Page 2: Contract management
│   │   ├── InvoicesDashboard.tsx     # Page 3: Invoice tracking
│   │   ├── AlertsDashboard.tsx       # Page 4: Alerts & recommendations
│   │   └── SimulationsDashboard.tsx  # Page 5: Financial simulations
│   ├── lib/
│   │   └── utils.ts              # Utility functions & API client
│   ├── App.tsx                   # Main app with routing
│   ├── main.tsx                  # App entry point
│   └── index.css                 # Tailwind directives
├── index.html
├── package.json
├── tailwind.config.js
└── tsconfig.json
```

## Visual Design

- **Color Palette:**
  - Primary: Blue (#0ea5e9)
  - Success: Green (#10b981)
  - Warning: Yellow (#f59e0b)
  - Danger: Red (#ef4444)
  - Purple: (#8b5cf6)

- **Typography:**
  - Clean, modern sans-serif fonts
  - Clear hierarchy with varied font weights
  - Readable sizes optimized for financial data

- **Components:**
  - Card-based layouts for organized information
  - Consistent spacing and padding
  - Subtle shadows for depth
  - Border accents for visual separation

## Browser Support

- Chrome/Edge (latest)
- Firefox (latest)
- Safari (latest)

## Performance

- Fast initial load with Vite
- Optimized bundle size
- Lazy loading for routes
- Efficient re-renders with React

---

**Built with Claude Code for FINCENTER**
