import {authorised,renderReport} from './report.mjs';
export const runtime='nodejs';
export const dynamic='force-dynamic';
export const maxDuration=60;
const privateHeaders={'Cache-Control':'private, no-store, max-age=0','X-Robots-Tag':'noindex, nofollow','Referrer-Policy':'no-referrer','X-Content-Type-Options':'nosniff','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'"};
export async function GET(request){
 const token=process.env.FEEDBACK_OWNER_TOKEN;
 if(!token||token.length<32)return new Response('Owner feedback access has not been configured.',{status:503,headers:privateHeaders});
 if(!authorised(request.headers.get('authorization'),token))return new Response('Sign in with the owner username and password.',{status:401,headers:{...privateHeaders,'WWW-Authenticate':'Basic realm="The Rehearsal private feedback", charset="UTF-8"'}});
 const url=new URL(request.url),days=Number(url.searchParams.get('days')||30),download=url.searchParams.get('download');
 if(!Number.isInteger(days)||days<1||days>365||download&&!['json','html'].includes(download))return new Response('Invalid report options.',{status:400,headers:privateHeaders});
 const backend=process.env.BACKEND_URL;
 if(!backend||process.env.VERCEL&&!process.env.API_PROXY_TOKEN)return new Response('Feedback backend is not configured.',{status:503,headers:privateHeaders});
 try{
  const response=await fetch(backend.replace(/\/$/,'')+'/api/owner/feedback?days='+days,{cache:'no-store',redirect:'error',signal:AbortSignal.timeout(50000),headers:{'x-rehearsal-token':process.env.API_PROXY_TOKEN||'','x-feedback-owner-token':token}});
  if(!response.ok)return new Response('Feedback could not be loaded. Check the owner configuration and try again.',{status:502,headers:privateHeaders});
  const data=await response.json();
  const json=download==='json';
  return new Response(json?JSON.stringify(data,null,2):renderReport(data,download==='html'),{headers:{...privateHeaders,'Content-Type':json?'application/json; charset=utf-8':'text/html; charset=utf-8',...(download?{'Content-Disposition':`attachment; filename="rehearsal-feedback-${days}-days.${download}"`}:{})}});
 }catch{return new Response('The feedback server is unavailable or still starting. Wait a moment and reload this page.',{status:504,headers:privateHeaders});}
}
