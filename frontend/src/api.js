// frontend/src/api.js
export async function getHealth() {
    const res = await fetch('/api/health');
    return res.json();
  }
  
  export async function getSamples() {
    const res = await fetch('/api/samples');
    return res.json();
  }
  
  export async function postPredict(payload) {
    const res = await fetch('/api/predict', {
      method: 'POST',
      headers: {'Content-Type':'application/json'},
      body: JSON.stringify(payload)
    });
    return res.json();
  }
  