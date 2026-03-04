import s from './ServiceSettings.module.css'

const ADMIN_ROLES = ['sys', 'admin']

export default function ServiceSettings({ currentUser }) {
  const canEdit = ADMIN_ROLES.includes(currentUser?.role)

  return (
    <div className={s.wrap}>
      {!canEdit && (
        <div style={{ padding: '8px 14px', marginBottom: 16, background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 6, fontSize: 13, color: '#ad8b00' }}>
          当前角色仅可查看，无法修改设置
        </div>
      )}
      <div className={s.statsRow}>
        <MetricCard label="CPU 使用率" value="23%" color="var(--color-success)" />
        <MetricCard label="内存使用" value="4.2 GB / 16 GB" color="var(--color-primary)" />
        <MetricCard label="磁盘使用" value="68%" color="var(--color-warning)" />
        <MetricCard label="运行时间" value="15天 8小时" color="var(--color-purple)" />
      </div>

      <Section title="服务参数">
        <Row label="最大并发查询数" value="50" />
        <Row label="单次查询超时" value="60秒" />
        <Row label="LLM 模型" value="DeepSeek-V3" />
        <Row label="缓存策略" value="4级 LRU 缓存（已启用）" />
        <Row label="最大返回行数" value="1000" />
      </Section>

      <Section title="告警设置">
        <Row label="CPU 告警阈值" value="80%" />
        <Row label="磁盘告警阈值" value="90%" />
        <Row label="异常登录检测" value="已启用" />
      </Section>

      <Section title="外部接口">
        <Row label="DeepSeek API" value="已连接" status="on" />
        <Row label="Coze 法规知识库" value="已连接" status="on" />
        <Row label="税收优惠数据库" value="1522条政策" status="on" />
      </Section>
    </div>
  )
}

function MetricCard({ label, value, color }) {
  return (
    <div className={s.metricCard}>
      <div className={s.metricValue} style={{ color }}>{value}</div>
      <div className={s.metricLabel}>{label}</div>
    </div>
  )
}

function Section({ title, children }) {
  return (
    <div className={s.section}>
      <h3 className={s.sectionTitle}>{title}</h3>
      <div className={s.sectionBody}>{children}</div>
    </div>
  )
}

function Row({ label, value, status }) {
  return (
    <div className={s.row}>
      <span className={s.rowLabel}>{label}</span>
      <span className={s.rowValue}>
        {status === 'on' && <span className={s.dot} />}
        {value}
      </span>
    </div>
  )
}
