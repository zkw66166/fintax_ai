import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  LineElement,
  PointElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js'
import { Bar } from 'react-chartjs-2'
import s from './ChartRenderer.module.css'

ChartJS.register(
  CategoryScale, LinearScale, BarElement, LineElement,
  PointElement, Title, Tooltip, Legend,
)

export default function ChartRenderer({ chartData }) {
  if (!chartData || !chartData.labels || !chartData.datasets) return null

  const { chartType, title, labels, datasets, options: rawOpts, percentageY } = chartData

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: { display: !!title, text: title, font: { size: 14 } },
      legend: { position: 'bottom', labels: { boxWidth: 12, padding: 10, font: { size: 12 } } },
      tooltip: {
        callbacks: {
          label: (ctx) => {
            const val = ctx.parsed.y
            if (val == null) return ''
            const ds = ctx.dataset
            if (percentageY || ds.yAxisID === 'y1') return `${ds.label}: ${val.toFixed(2)}%`
            if (Math.abs(val) >= 1e8) return `${ds.label}: ${(val / 1e8).toFixed(2)}亿`
            if (Math.abs(val) >= 1e4) return `${ds.label}: ${(val / 1e4).toFixed(2)}万`
            return `${ds.label}: ${val.toLocaleString()}`
          },
        },
      },
    },
    scales: {
      y: {
        type: 'linear',
        position: 'left',
        ticks: percentageY
          ? { callback: (v) => `${v}%` }
          : {
              callback: (v) => {
                if (Math.abs(v) >= 1e8) return `${(v / 1e8).toFixed(1)}亿`
                if (Math.abs(v) >= 1e4) return `${(v / 1e4).toFixed(0)}万`
                return v.toLocaleString()
              },
            },
      },
    },
  }

  // Add right Y axis for combo charts
  if (chartType === 'combo' || datasets.some((d) => d.yAxisID === 'y1')) {
    options.scales.y1 = {
      type: 'linear',
      position: 'right',
      grid: { drawOnChartArea: false },
      ticks: { callback: (v) => `${v}%` },
    }
  }

  const data = { labels, datasets }

  return (
    <div className={s.wrap}>
      <div className={s.chartBox}>
        <Bar data={data} options={options} />
      </div>
    </div>
  )
}
