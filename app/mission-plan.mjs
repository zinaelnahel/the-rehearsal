export function sourceNotice(method){
 return {
  reviewed_pdf_ocr:'Source: uploaded PDF; OCR text reviewed by you.',
  pasted_transcript:'Source: user-pasted transcript; not fetched from the video.',
  pasted_listing_text:'Source: your pasted advert text; not fetched from the site.',
  public_page:'Source: public-page snapshot; check the original for updates.'
 }[method]||null;
}
export function validGoalText(text){
 return typeof text==='string'&&text.trim().length>=3&&text.trim().length<=180&&!/^mission goal\s*\d+$/i.test(text.trim());
}
export function validatedMissionGoals(goals){
 if(!Array.isArray(goals)||goals.length<1||goals.length>5||goals.some(g=>!g||typeof g.id!=='string'||!validGoalText(g.text))||new Set(goals.map(g=>g.id)).size!==goals.length)throw Error('The mission goals could not be loaded. Please build the mission again.');
 return goals.map(g=>({...g,text:g.text.trim()}));
}
