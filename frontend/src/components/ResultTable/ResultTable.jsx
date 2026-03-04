import s from './ResultTable.module.css'

/**
 * ResultTable renders formatted table data.
 * Props:
 *   - displayData: { headers: string[], rows: object[] } (from backend display_data.table)
 *   - results: raw result rows (fallback if displayData not provided)
 *   - rowCount: number of raw result rows
 */
export default function ResultTable({ displayData, results, rowCount }) {
  // Use formatted display data if available
  if (displayData && displayData.headers && displayData.rows && displayData.rows.length > 0) {
    const { headers, rows } = displayData
    const count = rowCount ?? rows.length
    const isNumStr = (v) => typeof v === 'string' && /^[-\d,.]+[万亿%]?$/.test(v.trim())

    return (
      <div>
        <div className={s.rowCount}>查询成功（{count} 行）</div>
        <div className={s.tableWrap}>
          <table className={s.table}>
            <thead>
              <tr>
                {headers.map((h) => (
                  <th key={h}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, i) => (
                <tr key={i}>
                  {headers.map((h) => (
                    <td key={h} className={isNumStr(row[h]) ? s.numCell : undefined}>
                      {row[h] ?? '-'}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    )
  }

  // Fallback: raw results (no display_data)
  if (!results || results.length === 0) {
    return (
      <div className={s.emptyTableState}>
        <p>📊 查询成功，但未找到符合条件的数据</p>
        <p className={s.hint}>提示：请检查查询期间公司数据是否正确导入</p>
      </div>
    )
  }
  const headers = Object.keys(results[0])
  const isNum = (v) => typeof v === 'number'

  return (
    <div>
      <div className={s.rowCount}>查询成功（{results.length} 行）</div>
      <div className={s.tableWrap}>
        <table className={s.table}>
          <thead>
            <tr>
              {headers.map((h) => (
                <th key={h}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {results.map((row, i) => (
              <tr key={i}>
                {headers.map((h) => (
                  <td key={h} className={isNum(row[h]) ? s.numCell : undefined}>
                    {row[h] ?? ''}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
