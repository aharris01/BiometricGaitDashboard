export default function App() {
  const dashUrl = 'http://localhost:8000/dash/'
  return (
    <div style={{ padding: 16 }}>
      <h1>Biometric Gait Dashboard</h1>
      <p><a href="/login">Go to Login</a></p>
      <p><a href="/dataset">Go to Dataset (protected)</a></p>
      <iframe
        src={dashUrl}
        width="80%"
        height="60%"
        title="Dash App"
        style={{ border: '0px solid #ccc' }}
      />
    </div>
  );
}
