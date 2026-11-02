// No automatic POST retries: a lost response must not duplicate sessions or turns.
export async function api(path,body,method='POST') {
  let response;
  try {
    response=await fetch('/api'+path,{
      method,cache:'no-store',
      headers:body instanceof FormData?{}:{'Content-Type':'application/json'},
      body:body===undefined?undefined:body instanceof FormData?body:JSON.stringify(body),
      signal:AbortSignal.timeout(65000)
    });
  } catch (error) {
    throw Error(error.name==='TimeoutError'
      ? 'The practice server took too long to respond. Wait a moment and retry.'
      : 'The request could not reach the server. Check your connection and retry. If you are uploading, select the file again.');
  }
  let raw;
  try { raw=await response.text(); } catch {
    throw Error('The connection was interrupted while receiving the response. Wait a moment and retry; for an upload, select the file again.');
  }
  let data;
  try { data=JSON.parse(raw); } catch {
    throw Error(response.status===413?'Maximum file size is 4 MB. Choose a smaller PDF or DOCX.'
      :`The server returned an unexpected response (${response.status}). Wait a moment and retry.`);
  }
  if (!response.ok) throw Error(typeof data.detail==='string'?data.detail:'Check the fields and try again.');
  return data;
}

export async function uploadDocument(file) {
  if (!file) throw Error('Choose a PDF or DOCX first.');
  if (!/\.(pdf|docx)$/i.test(file.name)) throw Error('Only PDF and DOCX files are supported.');
  if (file.size>4*1024*1024) throw Error('Maximum file size is 4 MB.');
  let bytes;
  try { bytes=await file.arrayBuffer(); } catch {
    throw Error('The selected file could not be read. It may have moved or changed. Select it again and retry.');
  }
  // Snapshot the selected file before fetch, so stale file handles fail locally
  // with a useful message rather than an opaque browser "Failed to fetch".
  const data=new FormData();
  data.append('file',new Blob([bytes],{type:file.type||'application/octet-stream'}),file.name);
  return api('/upload',data);
}

export async function deleteSession(id) {
  const result=await api('/sessions/'+id,undefined,'DELETE');
  if (!result.deleted) throw Error('The server did not confirm deletion. Please retry.');
  let response;
  try { response=await fetch('/api/sessions/'+id+'/status',{cache:'no-store',signal:AbortSignal.timeout(65000)}); } catch {
    throw Error('Deletion was requested, but the connection failed before verification. Retry to confirm deletion.');
  }
  if (response.status!==404) throw Error('Deletion could not be verified. Please retry before leaving.');
}
