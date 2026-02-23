import {
  Chart as ChartJS, CategoryScale, LinearScale,
  BarElement, LineElement, PointElement, ArcElement,
  Title, Tooltip, Legend, Filler,
} from 'chart.js'
import { Pie, Bar, Line } from 'react-chartjs-2'
import s from './MiniChart.module.css'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, ArcElement, Title, Tooltip, Legend, Filler,
)

const CHART_MAP = { pie: Pie, bar: Bar, line: Line }

const PIE_COLORS = ['#3b82f6', '#8b5cf6', '#10b981', '#f59e0b', '#ef4444', '#06b6d4']

const BASE_OPTS = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: { position: 'bottom', labels: { boxWidth: 10, padding: 8, font: { size: 11 } } },
    title: { display: false },
  },
}

export default function MiniChart({ type = 'bar', title, labels, datasets, height = 200 }) {
  if (!labels || !datasets) return null
  const Comp = CHART_MAP[type]
  if (!Comp) return null

  const data = { labels, datasets: [...datasets] }

  // Auto-assign colors for pie charts
  if (type === 'pie' && data.datasets[0] && !data.datasets[0].backgroundColor) {
    data.datasets[0].backgroundColor = PIE_COLORS.slice(0, labels.length)
    data.datasets[0].borderColor = '#ffffff'
    data.datasets[0].borderWidth = 2
  }

  const opts = {
    ...BASE_OPTS,
    plugins: {
      ...BASE_OPTS.plugins,
      title: title ? { display: true, text: title, font: { size: 13, weight: '600' }, color: '#475569' } : { display: false },
    },
  }

  if (type === 'bar') {
    opts.scales = {
      y: {
        beginAtZero: true,
        grid: { color: '#f3f4f6' },
        ticks: {
          callback: (v) => Math.abs(v) >= 1e4 ? `${(v / 1e4).toFixed(0)}万` : v.toLocaleString(),
          font: { size: 10 },
        },
      },
      x: { ticks: { font: { size: 10 } }, grid: { display: false } },
    }
    opts.plugins.legend = { display: false }
    // Apply borderRadius to bar datasets
    data.datasets = data.datasets.map(ds => ({ ...ds, borderRadius: 0 }))
  }

  if (type === 'line') {
    opts.scales = {
      y: {
        beginAtZero: true,
        grid: { color: '#f3f4f6' },
        ticks: { font: { size: 10 } },
      },
      x: { ticks: { font: { size: 10 } }, grid: { display: false } },
    }
    // Apply smooth curve + area fill
    data.datasets = data.datasets.map(ds => ({
      ...ds,
      tension: 0.3,
      fill: true,
      backgroundColor: (ds.borderColor || '#3b82f6') + '33',
    }))
  }

  return (
    <div className={s.wrap} style={{ height }}>
      <Comp data={data} options={opts} />
    </div>
  )
}
