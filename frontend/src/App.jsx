// frontend/src/App.jsx
import { useEffect, useState } from 'react'
import { getHealth, getSamples, postPredict } from './api'

export default function App() {
  const [health, setHealth] = useState(null)
  const [rows, setRows] = useState([])

  useEffect(() => {
    getHealth().then(setHealth)
    getSamples().then(setRows)
  }, [])

  const runPredict = async () => {
    const out = await postPredict({ x: 42, msg: 'hello' })
    alert(JSON.stringify(out, null, 2))
  }

  return (
    <div style={{padding:16}}>
      <h1>React ↔ Dash Backend</h1>
      <p>Health: {health ? health.status : '...'}</p>

      <h2>Samples</h2>
      <ul>
        {rows.map(r => <li key={r.id}>{r.name}: {r.value}</li>)}
      </ul>

      <button onClick={runPredict}>Test POST /api/predict</button>

      <p style={{marginTop:24}}>
        Optional Dash page (backend): <a href="http://127.0.0.1:8000/dash/" target="_blank">/dash/</a>
      </p>
    </div>
  )
}
