import { useEffect, useState } from "react";
import { apiGet, clearToken } from "../auth";
import { useNavigate } from "react-router-dom";

export default function DatasetPage(){
  const [rows, setRows] = useState([]);
  const [err, setErr] = useState("");
  const nav = useNavigate();

  useEffect(()=>{
    apiGet("/api/samples").then(setRows).catch(e=>setErr(e.message));
  },[]);

  return (
    <div style={{padding:16}}>
      <h1>Dataset</h1>
      <button onClick={()=>{ clearToken(); nav("/login", {replace:true}); }}>Log out</button>
      {err && <p style={{color:"crimson"}}>Error: {err}</p>}
      <ul>
        {rows.map(r => <li key={r.id}>{r.name}: {r.value}</li>)}
      </ul>
    </div>
  );
}
