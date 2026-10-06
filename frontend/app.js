const $=s=>document.querySelector(s);
const labels={first_name:"ชื่อ / First name",last_name:"นามสกุล / Last name",date_of_birth:"วันเกิด / Date of birth",monthly_salary:"รายได้ต่อเดือน / Monthly salary",email:"อีเมล / Email"};
let running=false,recognition=null,interimMessage=null,transcriptQueue=Promise.resolve(),audioContext=null,playbackTime=0;
function esc(x){return String(x??'').replace(/[&<>'"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"}[c]));}
function add(who,text,ai=false){if(!text)return;const d=document.createElement('div');d.className='msg '+(ai?'ai':'');d.innerHTML=`<div class="who">${esc(who)}</div><div class="bubble">${esc(text)}</div>`;$('#messages').appendChild(d);$('#messages').scrollTop=$('#messages').scrollHeight;}
function playPcm16(encoded){if(!encoded)return;const raw=Uint8Array.from(atob(encoded),char=>char.charCodeAt(0));if(raw.length<2||raw.length%2)return;audioContext=audioContext||new AudioContext();const samples=new Float32Array(raw.length/2);const view=new DataView(raw.buffer);for(let i=0;i<samples.length;i++)samples[i]=view.getInt16(i*2,true)/32768;const buffer=audioContext.createBuffer(1,samples.length,24000);buffer.copyToChannel(samples,0);const source=audioContext.createBufferSource();source.buffer=buffer;source.connect(audioContext.destination);playbackTime=Math.max(audioContext.currentTime,playbackTime);source.start(playbackTime);playbackTime+=buffer.duration;}
function setInterimTranscript(text){if(!text){if(interimMessage){interimMessage.remove();interimMessage=null;}return;}if(!interimMessage){interimMessage=document.createElement('div');interimMessage.className='msg';const who=document.createElement('div');who.className='who';who.textContent='Recognizing...';const bubble=document.createElement('div');bubble.className='bubble';interimMessage.append(who,bubble);$('#messages').appendChild(interimMessage);}interimMessage.querySelector('.bubble').textContent=text;$('#messages').scrollTop=$('#messages').scrollHeight;}
function setMode(v){$('#mode').textContent=v;$('#mode').className='badge '+(v==='ANSWER'?'answer':'listen');$('#dMode').textContent=v;}
function renderForm(values,status){$('#form').innerHTML=Object.entries(values).map(([k,v])=>`<div class="field"><span>${labels[k]||k}</span><span class="${v?'complete':'missing'}">${v?'✓ '+esc(v):'○ Missing'}</span></div>`).join('');$('#progress').textContent=`Completed: ${status.complete.length} / ${status.complete.length+status.incomplete.length}`;}
function renderReq(files){$('#requirements').innerHTML=Object.entries(files||{}).map(([k,v])=>`<div class="file"><b>${esc(k)}</b>: ${esc(v)}</div>`).join('');}
async function state(){const s=await(await fetch('/api/state')).json();setMode(s.mode);renderForm(s.form,s.status);$('#dAgent').textContent=s.agent;renderReq(s.requirements_loaded);}
function handleSkill(x){const skill=x.skill||{};$('#dAction').textContent=skill.action||'-';$('#dSkill').textContent=skill.skill_source||'-';if(skill.action==='FIND'&&skill.found&&skill.answer&&x.mode==='LISTEN')add('PRU-Agent',skill.answer,true);if(skill.action==='FILL'){renderForm(x.form,x.status);}if(!x.guard.allowed)add('PRU-Agent',x.guard.response,true);}
async function submitTranscript(text){
 const role=$('#role').value;
 add(role==='sales'?'Sales':'Customer',text);
 $('#voiceStatus').textContent='Transcript recognized; sending text to guardrails and skills...';
 try{
  const response=await fetch('/api/transcript',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,role})});
  const result=await response.json();
  if(!response.ok)throw new Error(result.detail||`Transcript request failed (${response.status})`);
  setMode(result.mode);
  $('#dGuard').textContent=result.guard.allowed?'PASS':`${result.guard.guard} (${result.guard.priority})`;
  handleSkill(result);
  if(result.mode==='ANSWER'&&result.guard.allowed){
   $('#voiceStatus').textContent='Sending your message to Foundry...';
   const answerResponse=await fetch('/api/answer',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text,role})});
   const answer=await answerResponse.json();
   if(!answerResponse.ok)throw new Error(answer.detail||`Foundry response failed (${answerResponse.status})`);
   if(answer.text)add('PRU-Agent',answer.text,true);
   if(answer.audio){
    if(audioContext)await audioContext.resume();
    playPcm16(answer.audio);
   }
   $('#voiceStatus').textContent=answer.text?'Foundry response received.':answer.audio?'Foundry is speaking.':'Foundry returned an empty response.';
  }else{
   $('#voiceStatus').textContent='Transcript sent to skills.';
  }
 }catch(error){
  $('#voiceStatus').textContent=`Message processing failed: ${error.message}`;
 }
}
async function startMic(){
 const SpeechRecognition=window.SpeechRecognition||window.webkitSpeechRecognition;
 if(!SpeechRecognition){
  $('#voiceStatus').textContent='SpeechRecognition is not supported in this browser. Use current Chrome or Edge.';
  throw new Error('Browser speech recognition is unavailable');
 }
 const activeRecognition=new SpeechRecognition();
 audioContext=audioContext||new AudioContext();
 await audioContext.resume();
 activeRecognition.lang=$('#speechLanguage').value;
 activeRecognition.continuous=true;
 activeRecognition.interimResults=true;
 activeRecognition.maxAlternatives=1;
 activeRecognition.onstart=()=>{
  running=true;
  $('#voiceStatus').textContent=`Listening in ${activeRecognition.lang}. Speak naturally; recognized text will be sent to Find/Fill skills.`;
 };
 activeRecognition.onresult=event=>{
  let interim='';
  for(let i=event.resultIndex;i<event.results.length;i++){
   const text=event.results[i][0].transcript.trim();
   if(!text)continue;
   if(event.results[i].isFinal){
    setInterimTranscript('');
    transcriptQueue=transcriptQueue.then(()=>submitTranscript(text));
   }else{
    interim+=`${text} `;
   }
  }
  setInterimTranscript(interim.trim());
 };
 activeRecognition.onerror=event=>{
  if(event.error==='aborted')return;
  $('#voiceStatus').textContent=`Speech recognition error: ${event.error}. Check microphone permission and browser speech service.`;
  if(event.error!=='no-speech'){
   running=false;
   $('#mic').textContent='🎤 Start microphone';
   $('#mic').classList.remove('recording');
  }
 };
 activeRecognition.onend=()=>{
  if(running){
   try{
    activeRecognition.start();
   }catch(error){
    running=false;
    $('#mic').textContent='🎤 Start microphone';
    $('#mic').classList.remove('recording');
    $('#voiceStatus').textContent=`Could not restart speech recognition: ${error.message}`;
   }
   return;
  }
  $('#voiceStatus').textContent='Speech recognition stopped.';
 };
 recognition=activeRecognition;
 activeRecognition.start();
 running=true;
 $('#mic').textContent='⏹ Stop microphone';
 $('#mic').classList.add('recording');
}
function stopMic(){running=false;if(recognition){recognition.stop();recognition=null;}setInterimTranscript('');$('#mic').textContent='🎤 Start microphone';$('#mic').classList.remove('recording');$('#voiceStatus').textContent='Speech recognition stopped.';}
$('#mic').onclick=async()=>{try{running?stopMic():await startMic();}catch(e){$('#voiceStatus').textContent=`Voice error: ${e.message}`;}};
$('#health').onclick=async()=>{$('#voiceStatus').textContent='Testing Foundry...';const r=await fetch('/api/health/foundry');const x=await r.json();$('#dFoundry').textContent=x.ok?'PASS':`FAIL: ${x.error||''}`;$('#voiceStatus').textContent=x.ok?'Foundry Voice Agent connection passed':x.message||'Foundry failed';};
$('#reset').onclick=async()=>{stopMic();transcriptQueue=Promise.resolve();await fetch('/api/reset',{method:'POST'});$('#messages').innerHTML='';await state();};
state();
