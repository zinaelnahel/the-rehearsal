'use client';
import {useI18n} from './i18n';

export default function CitedReply({content,sources,onView}){
 const {t}=useI18n();
 const parts=[];
 let cursor=0;
 for(const match of content.matchAll(/\[(\d+)\]/g)){
  parts.push(content.slice(cursor,match.index));
  const source=sources?.find(item=>item.id===match[1]);
  parts.push(source?<button key={match.index} type="button" className="inline-citation" aria-label={t('View source')+' ['+source.id+']'} onClick={()=>onView(source)}>{match[0]}</button>:match[0]);
  cursor=match.index+match[0].length;
 }
 parts.push(content.slice(cursor));
 return <>{parts}</>;
}
