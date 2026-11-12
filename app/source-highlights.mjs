// Highlight only exact excerpts present in both the cited passage and page.
export function highlightRanges(text, passage, excerpts = []) {
 const ranges = [];
 for (const quote of excerpts) {
  if (typeof quote !== 'string' || !quote.trim() || !passage.includes(quote)) continue;
  // Restrict matches to this passage's position, avoiding repeated page text.
  const passageStart = text.indexOf(passage);
  if (passageStart < 0) continue;
  const start = passageStart + passage.indexOf(quote);
  ranges.push([start, start + quote.length]);
 }
 ranges.sort((a,b)=>a[0]-b[0]);
 const merged=[];
 for(const range of ranges){
  const previous=merged.at(-1);
  if(previous&&range[0]<=previous[1])previous[1]=Math.max(previous[1],range[1]);
  else merged.push([...range]);
 }
 return merged;
}
