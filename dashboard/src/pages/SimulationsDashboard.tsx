import { useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'
import { Zap, TrendingUp, DollarSign, Percent, Brain, AlertTriangle } from 'lucide-react'

const API_BASE = 'http://localhost:8080'

interface AIScenario {
  id?: string
  name: string
  probability: number
  description: string
  budget_impact_pct: number
  cashflow_impact_pct: number
  key_risks: string[]
  recommended_actions: string[]
}

export function SimulationsDashboard() {
  const [activeTab, setActiveTab] = useState<'sliders' | 'ai'>('sliders')
  const [budgetCut, setBudgetCut] = useState(10)
  const [revenueGrowth, setRevenueGrowth] = useState(5)
  const [inflationRate, setInflationRate] = useState(3)
  const [aiScenarios, setAiScenarios] = useState<AIScenario[]>([])
  const [generatingAI, setGeneratingAI] = useState(false)
  const [aiError, setAiError] = useState<string | null>(null)

  const generateAIScenarios = async () => {
    setGeneratingAI(true)
    setAiError(null)
    try {
      const res = await fetch(`${API_BASE}/api/simulations/ai-generate`, { method: 'POST' })
      if (res.ok) {
        const data = await res.json()
        const scenarios: AIScenario[] = (data.scenarios ?? []).map((s: any) => ({
          ...s,
          key_risks: Array.isArray(s.key_risks) ? s.key_risks : JSON.parse(s.key_risks || '[]'),
          recommended_actions: Array.isArray(s.recommended_actions)
            ? s.recommended_actions
            : JSON.parse(s.recommended_actions || '[]'),
        }))
        setAiScenarios(scenarios)
      } else {
        setAiError('Failed to generate scenarios. Please try again.')
      }
    } catch {
      setAiError('Connection error. Make sure the API server is running.')
    } finally {
      setGeneratingAI(false)
    }
  }

  // Base budget data
  const baseMonthlyBudget = 1000000 // $1M per month

  // Seasonal multipliers — Q4 spike, Q1 dip, summer slowdown
  const SEASONAL = [0.88, 0.91, 0.97, 1.02, 1.05, 0.98, 0.93, 0.95, 1.04, 1.08, 1.12, 1.24]

  // Generate simulation data with realistic variation
  const generateSimulationData = () => {
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const data = months.map((month, index) => {
      const seasonal = SEASONAL[index]
      const monthlyInflation = Math.pow(1 + inflationRate / 100, (index + 1) / 12)
      const monthlyGrowth   = Math.pow(1 + revenueGrowth  / 100, (index + 1) / 12)
      const cutFactor = 1 - (budgetCut / 100)

      const baseline      = baseMonthlyBudget * seasonal
      const withCuts      = baseline * cutFactor
      const withInflation = baseline * monthlyInflation
      const optimized     = baseline * cutFactor * monthlyGrowth * 0.97  // cuts + efficiency gain

      return {
        month,
        baseline:      Math.round(baseline      / 1000),
        withCuts:      Math.round(withCuts       / 1000),
        withInflation: Math.round(withInflation  / 1000),
        optimized:     Math.round(optimized      / 1000),
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

  const getImpactColor = (pct: number) => {
    if (pct > 0) return 'text-green-600'
    if (pct < -10) return 'text-red-600'
    return 'text-yellow-600'
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Simulations & Scenarios</h2>
        <p className="text-gray-500 mt-1">Interactive financial modeling and scenario planning</p>
      </div>

      {/* Tab Switcher */}
      <div className="flex gap-2">
        <button
          onClick={() => setActiveTab('sliders')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'sliders'
              ? 'bg-primary-600 text-white'
              : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
          }`}
        >
          <Zap className="w-4 h-4" />
          Manual Scenarios
        </button>
        <button
          onClick={() => setActiveTab('ai')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
            activeTab === 'ai'
              ? 'bg-primary-600 text-white'
              : 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50'
          }`}
        >
          <Brain className="w-4 h-4" />
          AI Scenarios
        </button>
      </div>

      {/* AI Scenarios Tab */}
      {activeTab === 'ai' && (
        <div className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>AI-Generated Financial Scenarios</CardTitle>
              <CardDescription>
                Llama-3.3-70B analyzes your live financial data and generates named risk scenarios with impact estimates.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <button
                onClick={generateAIScenarios}
                disabled={generatingAI}
                className="flex items-center gap-2 px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 transition-colors font-medium"
              >
                <Brain className={`w-5 h-5 ${generatingAI ? 'animate-pulse' : ''}`} />
                {generatingAI ? 'Generating scenarios...' : 'Generate AI Scenarios'}
              </button>
              {generatingAI && (
                <p className="text-sm text-gray-500 mt-3">
                  Analyzing budget overruns, overdue invoices, and expiring contracts...
                </p>
              )}
              {aiError && (
                <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                  <p className="text-sm text-red-700">
                    <AlertTriangle className="w-4 h-4 inline mr-1" />
                    {aiError}
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          {aiScenarios.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {aiScenarios.map((scenario, idx) => (
                <Card key={idx} className="flex flex-col">
                  <CardHeader>
                    <div className="flex items-start justify-between">
                      <CardTitle className="text-base">{scenario.name}</CardTitle>
                      <span className="text-sm font-bold text-gray-600 whitespace-nowrap ml-2">
                        {(scenario.probability * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
                      <div
                        className="bg-primary-600 h-1.5 rounded-full"
                        style={{ width: `${scenario.probability * 100}%` }}
                      />
                    </div>
                    <CardDescription className="mt-2">{scenario.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="flex-1 space-y-4">
                    {/* Impact Metrics */}
                    <div className="grid grid-cols-2 gap-3">
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">Budget Impact</p>
                        <p className={`text-xl font-bold ${getImpactColor(scenario.budget_impact_pct)}`}>
                          {scenario.budget_impact_pct > 0 ? '+' : ''}{scenario.budget_impact_pct}%
                        </p>
                      </div>
                      <div className="bg-gray-50 rounded-lg p-3">
                        <p className="text-xs text-gray-500">Cashflow Impact</p>
                        <p className={`text-xl font-bold ${getImpactColor(scenario.cashflow_impact_pct)}`}>
                          {scenario.cashflow_impact_pct > 0 ? '+' : ''}{scenario.cashflow_impact_pct}%
                        </p>
                      </div>
                    </div>

                    {/* Key Risks */}
                    {scenario.key_risks.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Key Risks</p>
                        <ul className="space-y-1">
                          {scenario.key_risks.map((risk, i) => (
                            <li key={i} className="text-xs text-gray-700 flex items-start gap-1">
                              <span className="text-red-400 mt-0.5">•</span>
                              {risk}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    {/* Recommended Actions */}
                    {scenario.recommended_actions.length > 0 && (
                      <div>
                        <p className="text-xs font-semibold text-gray-600 mb-1">Recommended Actions</p>
                        <ul className="space-y-1">
                          {scenario.recommended_actions.map((action, i) => (
                            <li key={i} className="text-xs text-gray-700 flex items-start gap-1">
                              <span className="text-green-500 mt-0.5">→</span>
                              {action}
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Manual Scenarios Tab */}
      {activeTab === 'sliders' && <>

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
              <YAxis domain={['auto', 'auto']} label={{ value: 'Budget ($K)', angle: -90, position: 'insideLeft' }} />
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

      </> /* end sliders tab */ }
    </div>
  )
}
