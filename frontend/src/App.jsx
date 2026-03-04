import { useState, useCallback, useRef } from 'react'
import styles from './App.module.css'
import useAuth from './hooks/useAuth'
import Login from './components/Login/Login'
import CaptchaModal from './components/CaptchaModal/CaptchaModal'
import Header from './components/Header/Header'
import Sidebar from './components/Sidebar/Sidebar'
import ChatArea from './components/ChatArea/ChatArea'
import HistoryPanel from './components/HistoryPanel/HistoryPanel'
import CompanyProfile from './components/CompanyProfile/CompanyProfile'
import DataManagementPage from './components/DataManagement/DataManagementPage'
import SystemSettingsPage from './components/SystemSettings/SystemSettingsPage'
import Dashboard from './components/Dashboard/Dashboard'
import Footer from './components/Footer/Footer'

export default function App() {
  const { user, loading, handleLogin, handleLogout, isAdmin } = useAuth()
  const [messages, setMessages] = useState([])
  const [historyItems, setHistoryItems] = useState([])
  const [responseMode, setResponseMode] = useState('detailed')
  const [thinkingMode, setThinkingMode] = useState('think')
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [pendingInputText, setPendingInputText] = useState('')
  const [currentPage, setCurrentPage] = useState('dashboard')
  const [captchaVerified, setCaptchaVerified] = useState(false)
  const chatAreaRef = useRef(null)
  const historyNavRef = useRef({})

  const handleHistoryClick = useCallback((entry) => {
    setPendingInputText(entry.query)

    const matchIndices = messages
      .map((m, i) => (m.role === 'user' && m.content === entry.query ? i : -1))
      .filter((i) => i !== -1)

    if (matchIndices.length > 0) {
      const key = entry.query
      const lastIdx = historyNavRef.current[key] ?? -1
      const nextPos = matchIndices.findIndex((i) => i > lastIdx)
      const targetIdx = nextPos !== -1 ? matchIndices[nextPos] : matchIndices[0]
      historyNavRef.current[key] = targetIdx
      chatAreaRef.current?.scrollToMessage(targetIdx)
    }
  }, [messages])

  const handleReinvoke = useCallback((historyIndex) => {
    // Trigger re-invocation via ChatArea
    if (chatAreaRef.current?.handleReinvoke) {
      chatAreaRef.current.handleReinvoke(historyIndex, thinkingMode)
    }
  }, [thinkingMode])

  if (loading) {
    return (
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: '100vh', color: '#999' }}>
        加载中...
      </div>
    )
  }

  if (!user && !captchaVerified) {
    return <CaptchaModal onVerified={() => setCaptchaVerified(true)} />
  }

  if (!user) {
    return <Login onLogin={handleLogin} />
  }

  const renderMainContent = () => {
    switch (currentPage) {
      case 'dashboard':
        return (
          <Dashboard
            selectedCompanyId={selectedCompanyId}
            onPageChange={setCurrentPage}
            onQueryClick={setPendingInputText}
            onCompanyChange={setSelectedCompanyId}
            user={user}
          />
        )
      case 'chat':
        return (
          <>
            <ChatArea
              ref={chatAreaRef}
              messages={messages}
              setMessages={setMessages}
              onQueryDone={(entry) => setHistoryItems((prev) => [entry, ...prev])}
              responseMode={responseMode}
              onResponseModeChange={setResponseMode}
              thinkingMode={thinkingMode}
              onThinkingModeChange={setThinkingMode}
              selectedCompanyId={selectedCompanyId}
              pendingInputText={pendingInputText}
              onPendingInputTextConsumed={() => setPendingInputText('')}
            />
            <HistoryPanel items={historyItems} setItems={setHistoryItems} onSelect={handleHistoryClick} onReinvoke={handleReinvoke} />
          </>
        )
      case 'profile':
        return <CompanyProfile selectedCompanyId={selectedCompanyId} />
      case 'data-management':
        return <DataManagementPage selectedCompanyId={selectedCompanyId} />
      case 'settings':
        return <SystemSettingsPage currentUser={user} />
      default:
        return null
    }
  }

  return (
    <div className={styles.layout} data-page={currentPage}>
      <Header
        selectedCompanyId={selectedCompanyId}
        onCompanyChange={setSelectedCompanyId}
        user={user}
        onLogout={handleLogout}
      />
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />
      {renderMainContent()}
      <Footer />
    </div>
  )
}
