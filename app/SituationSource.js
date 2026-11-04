'use client';

export default function SituationSource({kind,onKindChange,text,setText,file,setFile,listingUrl,setListingUrl,listingText,setListingText,disabled,onError}){
 return <div>
  <label htmlFor="situation-source-kind">How would you like to add context?</label>
  <select id="situation-source-kind" value={kind} disabled={disabled} onChange={e=>onKindChange(e.target.value)}>
   <option value="text">Describe your situation or paste text</option>
   <option value="file">Upload a document</option>
   <option value="listing">Use a listing link (optional)</option>
  </select>
  {kind==='text'?<div className="input-area"><label htmlFor="document">Situation notes or document text</label><textarea id="document" maxLength={100000} value={text} disabled={disabled} onChange={e=>setText(e.target.value)} rows={8} placeholder="Describe the situation, who you are speaking to, and the facts you know. Or paste a document…"/><small>{text.length.toLocaleString()} / 100,000 characters</small></div>
  :kind==='file'?<div className="upload-area"><span className="upload-icon">↥</span><h3>Your document, your context</h3><p>Text-based PDF or DOCX · up to 4 MB</p><input id="upload" type="file" accept=".pdf,.docx" disabled={disabled} onChange={e=>{const selected=e.target.files?.[0];if(selected&&selected.size>4*1024*1024){onError('Maximum file size is 4 MB.');e.target.value='';return;}setFile(selected);}}/><p className="subtle">{file?file.name:'Scanned PDFs are not supported.'}</p></div>
  :<div className="listing-input"><label htmlFor="listing-url">Idealista listing URL</label><input id="listing-url" type="url" maxLength={2048} value={listingUrl} disabled={disabled} onChange={e=>setListingUrl(e.target.value)} placeholder="https://www.idealista.com/inmueble/…/"/><p>Spain, Portugal or Italy. Use a direct advert link, not a search page.</p><label htmlFor="listing-text">Advert text (optional fallback)</label><textarea id="listing-text" maxLength={100000} rows={6} value={listingText} disabled={disabled} onChange={e=>setListingText(e.target.value)} placeholder="If the site blocks reading, paste the advert’s price, description and features here."/><p className="listing-note">Pasted text is used without fetching the page. Otherwise, the server requests the public listing. Blocked pages and login walls are not bypassed.</p></div>}
 </div>;
}
