'use client';
import {useState} from 'react';
import {MediaSource} from './Speech';
import VideoSource from './VideoSource';

export default function MediaSources({language,disabled,speechEnabled,onChange}){
 const [kind,setKind]=useState('link');
 return <div><label htmlFor="media-source-kind">How would you like to add media?</label>
 <select id="media-source-kind" value={kind} disabled={disabled} onChange={e=>{onChange(null);setKind(e.target.value);}}>
  <option value="link">Use a video link</option>
  {speechEnabled&&<option value="upload">Record or upload audio / video</option>}
 </select>
 {kind==='upload'&&speechEnabled?<MediaSource language={language} disabled={disabled} onChange={onChange}/>:<VideoSource language={language} disabled={disabled} onChange={onChange}/>}
 </div>;
}
