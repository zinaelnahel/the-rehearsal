// Server-only proxy: provider keys and the backend token never enter browser code.
export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';
export const maxDuration = 60;
const MAX_BODY = 4 * 1024 * 1024 + 65536;

async function proxy(request, context) {
  const {path} = await context.params;
  if (!path?.length || path.some(segment => !/^[a-zA-Z0-9_-]+$/.test(segment))) {
    return Response.json({detail:'Invalid API path.'},{status:400});
  }
  const origin = request.headers.get('origin');
  if (!['GET','HEAD'].includes(request.method) && origin) {
    try {
      if (new URL(origin).host !== request.headers.get('host')) {
        return Response.json({detail:'Origin not allowed.'},{status:403});
      }
    } catch { return Response.json({detail:'Invalid origin.'},{status:403}); }
  }
  const backend = process.env.BACKEND_URL || 'http://127.0.0.1:8000';
  if (process.env.VERCEL && (!process.env.BACKEND_URL || !process.env.API_PROXY_TOKEN)) {
    return Response.json({detail:'Deployment requires BACKEND_URL and API_PROXY_TOKEN on the server.'},{status:503});
  }
  const headers = new Headers();
  const type = request.headers.get('content-type');
  if (type) headers.set('content-type',type);
  if (process.env.API_PROXY_TOKEN) headers.set('x-rehearsal-token',process.env.API_PROXY_TOKEN);
  let body;
  if (!['GET','HEAD'].includes(request.method)) {
    const reader = request.body?.getReader();
    const chunks = [];
    let size = 0;
    try {
      while (reader) {
        const {done,value} = await reader.read();
        if (done) break;
        size += value.byteLength;
        if (size > MAX_BODY) {
          await reader.cancel();
          return Response.json({detail:'Maximum upload size is 4 MB.'},{status:413});
        }
        chunks.push(value);
      }
    } catch {
      return Response.json({detail:'The upload was interrupted. Select the file again and retry.'},{status:400});
    }
    if (size) {
      body = Buffer.concat(chunks);
      headers.set('content-length',String(size));
    }
  }
  try {
    const result = await fetch(`${backend.replace(/\/$/,'')}/api/${path.join('/')}`, {
      method:request.method,headers,body,cache:'no-store',redirect:'error',
      signal:AbortSignal.timeout(55000)
    });
    return new Response(result.body, {status:result.status,headers:{
      'content-type':result.headers.get('content-type') || 'application/json',
      'cache-control':'no-store'
    }});
  } catch (error) {
    const timedOut=['TimeoutError','AbortError'].includes(error.name);
    return Response.json({detail:timedOut
      ? 'The practice server took too long to respond. It may be waking up. Wait a moment, then retry.'
      : 'The practice server could not be reached. Check your connection and retry. Your document may need to be selected again.'
    },{status:timedOut?504:502,headers:{'cache-control':'no-store'}});
  }
}
export {proxy as GET, proxy as POST, proxy as PUT, proxy as DELETE};
