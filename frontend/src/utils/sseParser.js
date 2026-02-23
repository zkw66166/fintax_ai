/**
 * Parse SSE events from a fetch Response using ReadableStream.
 * Yields {event, data} objects.
 */
export async function* parseSSE(response) {
  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8', { stream: true })
  let buf = ''
  let currentEvent = ''
  let currentData = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buf += decoder.decode(value, { stream: true })

    const lines = buf.split('\n')
    buf = lines.pop() // keep incomplete line

    for (const line of lines) {
      if (line.startsWith('event: ')) {
        currentEvent = line.slice(7).trim()
      } else if (line.startsWith('data: ')) {
        currentData = line.slice(6)
      } else if (line === '') {
        // blank line = end of event
        if (currentEvent && currentData) {
          try {
            yield { event: currentEvent, data: JSON.parse(currentData) }
          } catch {
            yield { event: currentEvent, data: currentData }
          }
        }
        currentEvent = ''
        currentData = ''
      }
    }
  }

  // flush remaining
  if (currentEvent && currentData) {
    try {
      yield { event: currentEvent, data: JSON.parse(currentData) }
    } catch {
      yield { event: currentEvent, data: currentData }
    }
  }
}
