import { useEffect, useState } from 'react'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/Card'
import { fetchAPI } from '../lib/utils'
import { TrendingUp, TrendingDown, DollarSign, AlertTriangle } from 'lucide-react'

interface BudgetSummary {
  department: string
  budget: number
  actual: number
  variance: number
}

const COLORS = ['#0ea5e9', '#8b5cf6', '#ec4899', '#f59e0b', '#10b981', '#ef4444', '#6366f1', '#14b8a6']

export function BudgetDashboard() {
  const [budgetData, setBudgetData] = useState<BudgetSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetchAPI<BudgetSummary[]>('/budgets/summary?year=2024')
      .then(data => {
        setBudgetData(data)
        setLoading(false)
      })
      .catch(err => {
        setError(err.message)
        setLoading(false)
      })
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-gray-500">Loading budget data...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-lg text-red-500">Error: {error}</div>
      </div>
    )
  }

  const totalBudget = budgetData.reduce((sum, item) => sum + item.budget, 0)
  const totalActual = budgetData.reduce((sum, item) => sum + item.actual, 0)
  const totalVariance = totalActual - totalBudget
  const variancePercent = ((totalVariance / totalBudget) * 100).toFixed(1)

  const chartData = budgetData.map(item => ({
    ...item,
    variancePercent: ((item.variance / item.budget) * 100).toFixed(1)
  }))

  const overBudgetDepts = budgetData.filter(d => d.variance > 0)
  const underBudgetDepts = budgetData.filter(d => d.variance < 0)

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold text-gray-900">Augmented Budget Dashboard</h2>
        <p className="text-gray-500 mt-1">Real-time budget variance tracking and analysis</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Total Budget</CardTitle>
            <DollarSign className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(totalBudget / 1000000).toFixed(2)}M</div>
            <p className="text-xs text-gray-500 mt-1">FY 2024</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Actual Spend</CardTitle>
            <DollarSign className="w-4 h-4 text-gray-400" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">${(totalActual / 1000000).toFixed(2)}M</div>
            <p className="text-xs text-gray-500 mt-1">
              {((totalActual / totalBudget) * 100).toFixed(1)}% of budget
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Variance</CardTitle>
            {totalVariance > 0 ? (
              <TrendingUp className="w-4 h-4 text-red-500" />
            ) : (
              <TrendingDown className="w-4 h-4 text-green-500" />
            )}
          </CardHeader>
          <CardContent>
            <div className={`text-2xl font-bold ${totalVariance > 0 ? 'text-red-600' : 'text-green-600'}`}>
              ${Math.abs(totalVariance / 1000000).toFixed(2)}M
            </div>
            <p className="text-xs text-gray-500 mt-1">
              {totalVariance > 0 ? '+' : ''}{variancePercent}%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium text-gray-600">Departments Over Budget</CardTitle>
            <AlertTriangle className="w-4 h-4 text-red-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-red-600">{overBudgetDepts.length}</div>
            <p className="text-xs text-gray-500 mt-1">
              {underBudgetDepts.length} under budget
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Budget vs Actual Bar Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Budget vs Actual by Department</CardTitle>
            <CardDescription>Comparison of planned budget and actual spending</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="department" angle={-45} textAnchor="end" height={100} />
                <YAxis />
                <Tooltip formatter={(value: number) => `$${(value / 1000000).toFixed(2)}M`} />
                <Legend />
                <Bar dataKey="budget" fill="#0ea5e9" name="Budget" />
                <Bar dataKey="actual" fill="#8b5cf6" name="Actual" />
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Budget Distribution Pie Chart */}
        <Card>
          <CardHeader>
            <CardTitle>Budget Distribution</CardTitle>
            <CardDescription>Allocation across departments</CardDescription>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={350}>
              <PieChart>
                <Pie
                  data={chartData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={(entry) => `${entry.department}: ${((entry.budget / totalBudget) * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="budget"
                >
                  {chartData.map((_, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip formatter={(value: number) => `$${(value / 1000000).toFixed(2)}M`} />
              </PieChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      </div>

      {/* Detailed Table */}
      <Card>
        <CardHeader>
          <CardTitle>Department Budget Details</CardTitle>
          <CardDescription>Detailed breakdown of budget performance</CardDescription>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b">
                  <th className="text-left py-3 px-4 font-semibold text-gray-900">Department</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-900">Budget</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-900">Actual</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-900">Variance</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-900">Variance %</th>
                  <th className="text-right py-3 px-4 font-semibold text-gray-900">Status</th>
                </tr>
              </thead>
              <tbody>
                {chartData.map((item, index) => (
                  <tr key={index} className="border-b hover:bg-gray-50">
                    <td className="py-3 px-4 font-medium">{item.department}</td>
                    <td className="text-right py-3 px-4">${(item.budget / 1000000).toFixed(2)}M</td>
                    <td className="text-right py-3 px-4">${(item.actual / 1000000).toFixed(2)}M</td>
                    <td className={`text-right py-3 px-4 font-semibold ${item.variance > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {item.variance > 0 ? '+' : ''}${(item.variance / 1000000).toFixed(2)}M
                    </td>
                    <td className={`text-right py-3 px-4 ${item.variance > 0 ? 'text-red-600' : 'text-green-600'}`}>
                      {item.variance > 0 ? '+' : ''}{item.variancePercent}%
                    </td>
                    <td className="text-right py-3 px-4">
                      {item.variance > 0 ? (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
                          Over Budget
                        </span>
                      ) : (
                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                          Under Budget
                        </span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
