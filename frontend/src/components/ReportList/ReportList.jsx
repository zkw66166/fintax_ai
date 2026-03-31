import { useState, useEffect, useCallback } from 'react'
import { ArrowLeft, Eye, Trash2, Loader2, FileText, Plus } from 'lucide-react'
import { fetchReports, deleteReport } from '../../services/api'
import s from './ReportList.module.css'

const STATUS_MAP = {
  generating: { label: '生成中', cls: 'statusGenerating' },
  completed: { label: '已完成', cls: 'statusCompleted' },
  failed: { label: '失败', cls: 'statusFailed' },
}

export default function ReportList({ companyId, onViewReport, onBack, showBackButton = true, onGenerateReport }) {
  const [reports, setReports] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const size = 20

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchReports(companyId || '', page, size)
      setReports(data.items || [])
      setTotal(data.total || 0)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }, [companyId, page])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id) => {
    if (!confirm('确定删除该报告？')) return
    try {
      await deleteReport(id)
      load()
    } catch (e) {
      alert('删除失败: ' + e.message)
    }
  }

  const totalPages = Math.ceil(total / size)

  return (
    <div className={s.listPage}>
      <div className={s.header}>
        {showBackButton && onBack && (
          <button className={s.backBtn} onClick={onBack}>
            <ArrowLeft size={16} /> 返回画像
          </button>
        )}
        <h2 className={s.title}>
          <FileText size={18} /> 分析报告列表
        </h2>
        <div className={s.headerActions}>
          {onGenerateReport && (
            <button className={s.generateBtn} onClick={onGenerateReport} title="生成分析报告">
              <Plus size={14} /> 生成报告
            </button>
          )}
          <span className={s.count}>共 {total} 份报告</span>
        </div>
      </div>

      {error && <div className={s.errorBar}>{error}</div>}

      {loading ? (
        <div className={s.loadingWrap}><Loader2 size={20} className={s.spin} /> 加载中...</div>
      ) : reports.length === 0 ? (
        <div className={s.emptyWrap}>暂无分析报告</div>
      ) : (
        <>
          <div className={s.tableWrap}>
            <table className={s.table}>
              <thead>
                <tr>
                  <th>纳税人名称</th>
                  <th>年度</th>
                  <th>提交用户</th>
                  <th>提交时间</th>
                  <th>生成时间</th>
                  <th>状态</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                {reports.map((r) => {
                  const st = STATUS_MAP[r.status] || STATUS_MAP.failed
                  return (
                    <tr key={r.id}>
                      <td className={s.nameCell}>{r.taxpayer_name}</td>
                      <td>{r.year}</td>
                      <td>{r.username}</td>
                      <td className={s.timeCell}>{r.created_at?.replace('T', ' ').slice(0, 19)}</td>
                      <td className={s.timeCell}>{r.completed_at?.replace('T', ' ').slice(0, 19) || '—'}</td>
                      <td><span className={`${s.badge} ${s[st.cls]}`}>{st.label}</span></td>
                      <td>
                        <div className={s.actions}>
                          {r.status === 'completed' && (
                            <button
                              className={s.viewBtn}
                              onClick={() => onViewReport({ mode: 'view', reportId: r.id, taxpayerName: r.taxpayer_name, year: r.year })}
                              title="查看"
                            >
                              <Eye size={14} />
                            </button>
                          )}
                          <button className={s.deleteBtn} onClick={() => handleDelete(r.id)} title="删除">
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>

          {totalPages > 1 && (
            <div className={s.pagination}>
              <button disabled={page <= 1} onClick={() => setPage(page - 1)}>上一页</button>
              <span>{page} / {totalPages}</span>
              <button disabled={page >= totalPages} onClick={() => setPage(page + 1)}>下一页</button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
