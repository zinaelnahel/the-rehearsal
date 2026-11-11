// Follow the horizontal tabs keyboard pattern, retaining native Tab navigation.
export function sourceTabKey(event,current,ids,select){
 const offset=event.key==='ArrowRight'?1:event.key==='ArrowLeft'?-1:0;
 if(!offset&&!['Home','End'].includes(event.key))return;
 event.preventDefault();
 const index=event.key==='Home'?0:event.key==='End'?ids.length-1:(ids.indexOf(current)+offset+ids.length)%ids.length;
 const next=ids[index];select(next);
 event.currentTarget.parentElement.querySelector('#source-tab-'+next)?.focus();
}
