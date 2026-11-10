export function youtubeId(value){
 try{
  const url=new URL(value);
  if(url.protocol!=='https:'||url.username||url.password||url.port)return null;
  let id;
  if(['youtu.be','www.youtu.be'].includes(url.hostname))id=url.pathname.slice(1);
  else if(['youtube.com','www.youtube.com','m.youtube.com'].includes(url.hostname)){
   id=url.pathname==='/watch'?url.searchParams.get('v'):url.pathname.match(/^\/(?:shorts|embed|live)\/([\w-]{11})\/?$/)?.[1];
  }
  return /^[\w-]{11}$/.test(id||'')?id:null;
 }catch{return null;}
}

export function videoEvidence(source){
 const id=youtubeId(source?.url);
 if(!id)return null;
 const timed=typeof source.start==='number'&&Number.isFinite(source.start)&&source.start>=0;
 const start=timed?Math.floor(source.start):0;
 const end=timed&&Number.isFinite(source.end)&&source.end>source.start?Math.ceil(source.end):null;
 const params=new URLSearchParams({start:String(start),playsinline:'1',rel:'0'});
 if(end!==null)params.set('end',String(end));
 return {timed,start,end,embed:`https://www.youtube-nocookie.com/embed/${id}?${params}`,external:`https://www.youtube.com/watch?v=${id}${timed?'&t='+start+'s':''}`};
}

export function videoTime(seconds){
 const value=Math.floor(seconds);
 return `${Math.floor(value/60)}:${String(value%60).padStart(2,'0')}`;
}
