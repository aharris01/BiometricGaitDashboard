import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { login } from "../auth";

export default function LoginPage(){
  const nav = useNavigate();
  const [id, setId] = useState("");
  const [pw, setPw] = useState("");
  const [err, setErr] = useState("");

  const submit = async (e)=>{
    e.preventDefault();
    setErr("");
    try{
      await login(id.trim(), pw);
      nav("/dataset", { replace:true });
    }catch(e){
      setErr(e.message);
    }
  };

  return (
    <div style={{maxWidth:420, margin:"64px auto", padding:24, border:"1px solid #ddd", borderRadius:12}}>
      <h1>UNB Login</h1>
      <form onSubmit={submit} style={{display:"grid", gap:12}}>
        <input placeholder="UNB username" value={id} onChange={e=>setId(e.target.value)} required />
        <input type="password" placeholder="Password" value={pw} onChange={e=>setPw(e.target.value)} required />
        <button type="submit">Sign in</button>
      </form>
      {err && <p style={{color:"crimson"}}>{err}</p>}
      <p style={{fontSize:12, color:"#666"}}>Credentials are verified against lambda.int.unb.ca.</p>
    </div>
  );
}
