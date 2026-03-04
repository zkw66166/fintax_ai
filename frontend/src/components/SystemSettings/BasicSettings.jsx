import s from './BasicSettings.module.css'
import { Settings2, ShieldCheck, Clock, HeadphonesIcon } from 'lucide-react'

const ADMIN_ROLES = ['sys', 'admin']

export default function BasicSettings({ currentUser }) {
  const canEdit = ADMIN_ROLES.includes(currentUser?.role)

  return (
    <div className={s.wrap}>
      {!canEdit && (
        <div style={{ padding: '8px 14px', marginBottom: 16, background: '#fffbe6', border: '1px solid #ffe58f', borderRadius: 6, fontSize: 13, color: '#ad8b00' }}>
          当前角色仅可查看，无法修改设置
        </div>
      )}
      <Section title="系统偏好" icon={<Settings2 size={16} />}>
        <Row label="深色模式" value={<Toggle disabled={!canEdit} />} />
        <Row label="界面语言" value="简体中文" />
      </Section>
      <Section title="安全设置" icon={<ShieldCheck size={16} />}>
        <Row label="密码过期策略" value="90天" />
        <Row label="自动登出时间" value="30分钟" />
        <Row label="登录失败锁定" value="5次后锁定15分钟" />
      </Section>
      <Section title="维护计划" icon={<Clock size={16} />}>
        <Row label="数据自动清理" value="每日 03:00" />
        <Row label="自动备份" value="每日 04:00" />
      </Section>
      <Section title="技术支持" icon={<HeadphonesIcon size={16} />}>
        <Row label="服务热线" value="400-888-0000" />
        <Row label="技术邮箱" value="support@fintax.ai" />
        <Row label="服务时间" value="工作日 09:00-18:00" />
      </Section>
    </div>
  )
}

function Section({ title, icon, children }) {
  return (
    <div className={s.section}>
      <h3 className={s.sectionTitle}>
        {icon && <span className={s.sectionIcon}>{icon}</span>}
        {title}
      </h3>
      <div className={s.sectionBody}>{children}</div>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div className={s.row}>
      <span className={s.rowLabel}>{label}</span>
      <span className={s.rowValue}>
        {typeof value === 'string' ? value : value}
      </span>
    </div>
  )
}

function Toggle({ disabled }) {
  return <span className={s.toggleOff} style={disabled ? { opacity: 0.5, cursor: 'not-allowed' } : {}}>{disabled ? '关闭（只读）' : '关闭'}</span>
}
