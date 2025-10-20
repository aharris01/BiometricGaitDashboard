// frontend/src/auth.js
const API_BASE = import.meta.env.VITE_API_BASE || ""; // keep empty for dev proxy

export function getToken(){ return localStorage.getItem("auth_token"); }
export function setToken(t){ localStorage.setItem("auth_token", t); }
export function clearToken(){ localStorage.removeItem("auth_token"); }

export async function login(id, password){
  const res = await fetch(`${API_BASE}/auth/unb-login`, {
    method: "POST",
    headers: { "Content-Type":"application/json" },
    body: JSON.stringify({ id, password })
  });
  if(!res.ok){
    const e = await res.json().catch(()=>({error:"Login failed"}));
    throw new Error(e.error || "Login failed");
  }
  const data = await res.json(); // { token }
  setToken(data.token);
  return data;
}

export async function apiGet(path){
  const t = getToken();
  const res = await fetch(`${API_BASE}${path}`, {
    headers: t ? { Authorization: `Bearer ${t}` } : {}
  });
  if(res.status === 401) throw new Error("Unauthorized");
  return res.json();
}
