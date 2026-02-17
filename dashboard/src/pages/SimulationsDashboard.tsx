import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Zap, TrendingUp, DollarSign, Percent } from 'lucide-react'

export function SimulationsDashboard() {
  const [budgetCut, setBudgetCut] = useState(10)
  const [revenueGrowth, setRevenueGrowth] = useState(5)
  const [inflationRate, setInflationRate] = useState(3)

  // Base budget data
  const baseMonthlyBudget = 1000000 // $1M per month

  // Generate simulation data
  const generateSimulationData = () => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const data = months.map((month, index) => {
      const baseline = baseMonthlyBudget
      const withCuts = baseline * (1 - budgetCut / 100)
      const withInflation = baseline * (1 + (inflationRate / 100) * (index / 12))
      const withGrowth = baseline * (1 + (revenueGrowth / 100) * (index / 12))

      return {
        month,
        baseline: baseline / 1000,
        withCuts: withCuts / 1000,
        withInflation: withInflation / 1000,
        optimized: (withCuts * 0.95 + withGrowth * 0.05) / 1000,
      }
    })
    return data
  }

  const simulationData = generateSimulationData()

  const calculateYearlyImpact = () => {
    const baselineYearly = baseMonthlyBudget * 12
    const withCutsYearly = baselineYearly * (1 - budgetCut / 100)
    const savings = baselineYearly - withCutsYearly

    return {
      baseline: baselineYearly,
      withCuts: withCutsYearly,
      savings,
      savingsPercent: budgetCut,
    }
  }

  const impact = calculateYearlyImpact()

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Simulations & Scenarios</h2>
        <p className="text-gray-500 mt-1">Interactive financial modeling and scenario planning</p>
      </div>

      {/* Control Panel */}
      <Card>
        <CardHeader>
          <CardTitle>Scenario Parameters</CardTitle>
          <CardDescription>Adjust parameters to simulate different financial scenarios</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* Budget Cut Slider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Budget Cut: {budgetCut}%
              </label>
              <input
                type="range"
                min="0"
                max="30"
                value={budgetCut}
                onChange={(e) => setBudgetCut(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0%</span>
                <span>30%</span>
              </div>
            </div>

            {/* Revenue Growth Slider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Revenue Growth: {revenueGrowth}%
              </label>
              <input
                type="range"
                min="0"
                max="20"
                value={revenueGrowth}
                onChange={(e) => setRevenueGrowth(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0%</span>
                <span>20%</span>
              </div>
            </div>

            {/* Inflation Rate Slider */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Inflation Rate: {inflationRate}%
              </label>
              <input
                type="range"
                min="0"
                max="10"
                value={inflationRate}
                onChange={(e) => setInflationRate(Number(e.target.value))}
                className="w-full h-2 bg-gray-200 rounded-lg appearance-none cursor-pointer accent-primary-600"
              />
              <div className="flex justify-between text-xs text-gray-500 mt-1">
                <span>0%</span>
                <span>10%</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Impact Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Baseline Budget</CardTitle>
            <DollarSign className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(impact.baseline / 1000000).toFixed(1)}M</div>
            <p className="text-xs text-gray-500 mt-1">Annual budget</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">With Budget Cuts</CardTitle>
            <Percent className="w-4 h-4 text-blue-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-blue-600">${(impact.withCuts / 1000000).toFixed(1)}M</div>
            <p className="text-xs text-gray-500 mt-1">Reduced spending</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Projected Savings</CardTitle>
            <TrendingUp className="w-4 h-4 text-green-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-green-600">${(impact.savings / 1000000).toFixed(1)}M</div>
            <p className="text-xs text-gray-500 mt-1">Annual savings</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Savings Rate</CardTitle>
            <Zap className="w-4 h-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-purple-600">{impact.savingsPercent.toFixed(1)}%</div>
            <p className="text-xs text-gray-500 mt-1">Of total budget</p>
          </CardContent>
        </Card>
      </div>

      {/* Simulation Chart */}
      <Card>
        <CardHeader>
          <CardTitle>12-Month Budget Projection</CardTitle>
          <CardDescription>Compare different scenarios over the fiscal year</CardDescription>
        </CardHeader>
        <CardContent>
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={simulationData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis label={{ value: 'Budget ($K)', angle: -90, position: 'insideLeft' }} />
              <Tooltip formatter={(value: number) => `$${value.toFixed(0)}K`} />
              <Legend />
              <Line
                type="monotone"
                dataKey="baseline"
                stroke="#6b7280"
                strokeWidth={2}
                name="Baseline"
                strokeDasharray="5 5"
              />
              <Line
                type="monotone"
                dataKey="withCuts"
                stroke="#0ea5e9"
                strokeWidth={2}
                name="With Budget Cuts"
              />
              <Line
                type="monotone"
                dataKey="withInflation"
                stroke="#ef4444"
                strokeWidth={2}
                name="With Inflation"
              />
              <Line
                type="monotone"
                dataKey="optimized"
                stroke="#10b981"
                strokeWidth={2}
                name="Optimized"
              />
            </LineChart>
          </ResponsiveContainer>
        </CardContent>
      </Card>

      {/* Scenario Presets */}
      <Card>
        <CardHeader>
          <CardTitle>Quick Scenarios</CardTitle>
          <CardDescription>Apply pre-configured scenarios for common situations</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <button
              onClick={() => {
                setBudgetCut(15)
                setRevenueGrowth(5)
                setInflationRate(3)
              }}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-left"
            >
              <h3 className="font-semibold text-gray-900 mb-1">Conservative Growth</h3>
              <p className="text-sm text-gray-500">15% cuts, 5% growth, 3% inflation</p>
            </button>

            <button
              onClick={() => {
                setBudgetCut(5)
                setRevenueGrowth(12)
                setInflationRate(2)
              }}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-left"
            >
              <h3 className="font-semibold text-gray-900 mb-1">Aggressive Expansion</h3>
              <p className="text-sm text-gray-500">5% cuts, 12% growth, 2% inflation</p>
            </button>

            <button
              onClick={() => {
                setBudgetCut(25)
                setRevenueGrowth(2)
                setInflationRate(6)
              }}
              className="p-4 border-2 border-gray-200 rounded-lg hover:border-primary-500 hover:bg-primary-50 transition-all text-left"
            >
              <h3 className="font-semibold text-gray-900 mb-1">Crisis Mode</h3>
              <p className="text-sm text-gray-500">25% cuts, 2% growth, 6% inflation</p>
            </button>
          </div>
        </CardContent>
      </Card>

      {/* Insights */}
      <Card>
        <CardHeader>
          <CardTitle>Scenario Insights</CardTitle>
          <CardDescription>Key takeaways from the current simulation</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {budgetCut > 20 && (
              <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
                <p className="text-sm text-red-800">
                  <span className="font-semibold">High Risk:</span> Budget cuts above 20% may impact operational capacity and employee morale.
                </p>
              </div>
            )}
            {revenueGrowth > 10 && (
              <div className="p-3 bg-green-50 border border-green-200 rounded-lg">
                <p className="text-sm text-green-800">
                  <span className="font-semibold">Growth Opportunity:</span> Strong revenue growth projection enables strategic investments.
                </p>
              </div>
            )}
            {inflationRate > 5 && (
              <div className="p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                <p className="text-sm text-yellow-800">
                  <span className="font-semibold">Inflation Alert:</span> High inflation rates will erode purchasing power. Consider cost adjustments.
                </p>
              </div>
            )}
            {budgetCut < 10 && revenueGrowth > 8 && (
              <div className="p-3 bg-blue-50 border border-blue-200 rounded-lg">
                <p className="text-sm text-blue-800">
                  <span className="font-semibold">Balanced Growth:</span> Current parameters suggest healthy growth with controlled spending.
                </p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
