import { useState, useCallback, useRef } from 'react'
import styles from './App.module.css'
import Header from './components/Header/Header'
import Sidebar from './components/Sidebar/Sidebar'
import ChatArea from './components/ChatArea/ChatArea'
import HistoryPanel from './components/HistoryPanel/HistoryPanel'
import CompanyProfile from './components/CompanyProfile/CompanyProfile'
import Footer from './components/Footer/Footer'

export default function App() {
  const [messages, setMessages] = useState([])
  const [historyItems, setHistoryItems] = useState([])
  const [responseMode, setResponseMode] = useState('detailed')
  const [selectedCompanyId, setSelectedCompanyId] = useState('')
  const [pendingInputText, setPendingInputText] = useState('')
  const [currentPage, setCurrentPage] = useState('chat')
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

  const isChat = currentPage === 'chat'

  return (
    <div className={styles.layout} data-page={currentPage}>
      <Header selectedCompanyId={selectedCompanyId} onCompanyChange={setSelectedCompanyId} />
      <Sidebar currentPage={currentPage} onPageChange={setCurrentPage} />
      {isChat ? (
        <>
          <ChatArea
            ref={chatAreaRef}
            messages={messages}
            setMessages={setMessages}
            onQueryDone={(entry) => setHistoryItems((prev) => [entry, ...prev])}
            responseMode={responseMode}
            onResponseModeChange={setResponseMode}
            selectedCompanyId={selectedCompanyId}
            pendingInputText={pendingInputText}
            onPendingInputTextConsumed={() => setPendingInputText('')}
          />
          <HistoryPanel items={historyItems} setItems={setHistoryItems} onSelect={handleHistoryClick} />
        </>
      ) : (
        <CompanyProfile selectedCompanyId={selectedCompanyId} />
      )}
      <Footer />
    </div>
  )
}
