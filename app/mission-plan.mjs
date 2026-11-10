export function sourceNotice(method){
 return {
  reviewed_pdf_ocr:'Source: uploaded PDF; OCR text reviewed by you.',
  pasted_transcript:'Source: user-pasted transcript; not fetched from the video.',
  pasted_listing_text:'Source: your pasted advert text; not fetched from the site.',
  public_page:'Source: public-page snapshot; check the original for updates.'
 }[method]||null;
}
export function validatedMissionGoals(goals){
 if(!Array.isArray(goals)||goals.length<1||goals.length>5||goals.some(g=>!g||typeof g.id!=='string'||typeof g.text!=='string'||g.text.trim().length<3||/^mission goal\s*\d+$/i.test(g.text.trim()))||new Set(goals.map(g=>g.id)).size!==goals.length)throw Error('The mission goals could not be loaded. Please build the mission again.');
 return goals.map(g=>({...g,text:g.text.trim()}));
}
