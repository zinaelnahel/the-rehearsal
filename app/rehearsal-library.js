// Browser-only learning archive. No fetch, server/session identifiers or media.
export const LIBRARY_DB='the-rehearsal-library';
const STORE='rehearsals';
const MAX_RECORDS=100,MAX_BYTES=8*1024*1024;
const scenarios=['apartment','interview','course','difficult'];
const languages=['English','German','Spanish'];
const statuses=['not_asked','confirmed','unknown','not_applicable','unverified'];
const text=(value,limit)=>{if(typeof value!=='string'||value.length>limit)throw Error('This rehearsal cannot be saved.');return value;};
const list=(value,limit,convert)=>{if(!Array.isArray(value)||value.length>limit)throw Error('This rehearsal cannot be saved.');return value.map(convert);};

export function archiveRecord(input,id,createdAt=new Date().toISOString()) {
  if(!scenarios.includes(input.scenario)||!languages.includes(input.language)||!languages.includes(input.feedbackLanguage)
    ||!['Everyday','B1','B2'].includes(input.level)||!['live','demo'].includes(input.mode)
    ||!Number.isInteger(input.take)||input.take<1||!input.debrief)throw Error('This rehearsal cannot be saved.');
  const record={schemaVersion:1,id:text(id,80),createdAt:text(createdAt,40),updatedAt:new Date().toISOString(),
    title:text(input.title.trim(),100),scenario:input.scenario,language:input.language,
    feedbackLanguage:input.feedbackLanguage,level:input.level,mode:input.mode,take:input.take,
    turns:list(input.turns,61,turn=>{
      if(!['user','assistant'].includes(turn.role))throw Error('This rehearsal cannot be saved.');
      return {role:turn.role,content:text(turn.content,4000)};
    }),
    debrief:{
      note:text(input.debrief.note,10000),
      goals:list(input.debrief.goals,5,goal=>{
        if(!statuses.includes(goal.answer_status)||typeof goal.achieved!=='boolean')throw Error('This rehearsal cannot be saved.');
        return {text:text(goal.text,180),achieved:goal.achieved,answer_status:goal.answer_status};
      }),
      feedback:list(input.debrief.feedback,10,note=>({quote:text(note.quote,4000),suggestion:text(note.suggestion,4000),explanation:text(note.explanation,10000)})),
      unanswered:list(input.debrief.unanswered,30,item=>text(item,4000)),
      phrases:list(input.debrief.phrases,30,item=>text(item,4000))
    }};
  if(!record.id||!record.title||!Number.isFinite(Date.parse(record.createdAt)))throw Error('This rehearsal cannot be saved.');
  if(new TextEncoder().encode(JSON.stringify(record)).length>1024*1024)throw Error('This rehearsal is too large to save in the browser.');
  return record;
}

function openLibrary() {
  return new Promise((resolve,reject)=>{
    let blocked=false;
    const unavailable=()=>reject(Error('Browser storage is unavailable. You can download the rehearsal instead.'));
    let request;
    try{if(!globalThis.indexedDB){unavailable();return;}request=indexedDB.open(LIBRARY_DB,1);}catch{unavailable();return;}
    request.onupgradeneeded=()=>request.result.createObjectStore(STORE,{keyPath:'id'});
    request.onerror=unavailable;
    request.onblocked=()=>{blocked=true;reject(Error('Close other tabs of this app and try the library again.'));};
    request.onsuccess=()=>{
      const db=request.result;
      if(blocked){db.close();return;}
      db.onversionchange=()=>db.close();
      resolve(db);
    };
  });
}

async function transaction(mode,action) {
  const db=await openLibrary();
  return new Promise((resolve,reject)=>{
    let value,failure;
    let tx;
    try{tx=db.transaction(STORE,mode);}catch{db.close();reject(Error('The library could not be updated. Browser storage may be full or blocked.'));return;}
    tx.oncomplete=()=>{db.close();resolve(value);};
    tx.onabort=tx.onerror=()=>{db.close();reject(failure||Error('The library could not be updated. Browser storage may be full or blocked.'));};
    try{action(tx.objectStore(STORE),result=>{value=result;},error=>{failure=error;tx.abort();});}
    catch(error){failure=error;tx.abort();}
  });
}

export async function listRehearsals() {
  const rows=await transaction('readonly',(store,done)=>{const request=store.getAll();request.onsuccess=()=>done(request.result);});
  let unreadable=0;
  const records=rows.flatMap(row=>{
    try{
      if(row.schemaVersion!==1)throw Error('Unknown version');
      const record=archiveRecord(row,row.id,row.createdAt);
      record.updatedAt=row.updatedAt;
      return [record];
    }catch{unreadable++;return [];}
  }).sort((a,b)=>b.createdAt.localeCompare(a.createdAt));
  return {records,unreadable};
}

export async function saveRehearsal(input,id) {
  // Reconstruct an allowlisted copy even if callers pass a whole server response.
  const record=archiveRecord(input,id);
  await transaction('readwrite',(store,done,fail)=>{
    const request=store.getAll();
    request.onsuccess=()=>{
     try {
      const rows=request.result;
      const previous=rows.find(row=>row.id===record.id);
      if(previous)record.createdAt=previous.createdAt;
      const remaining=rows.filter(row=>row.id!==record.id);
      const bytes=new TextEncoder().encode(JSON.stringify([...remaining,record])).length;
      if(remaining.length>=MAX_RECORDS||bytes>MAX_BYTES){fail(Error('Your library is full. Delete a saved rehearsal or download a copy before saving more.'));return;}
      store.put(record);done(record);
     } catch {fail(Error('The library could not be updated. Browser storage may be full or blocked.'));}
    };
  });
  return record;
}

export function deleteRehearsal(id) {
  return transaction('readwrite',(store)=>store.delete(id));
}

export function clearRehearsals() {
  return transaction('readwrite',store=>store.clear());
}
