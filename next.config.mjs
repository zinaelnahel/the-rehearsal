import {execFileSync} from 'node:child_process';

let revision=process.env.REHEARSAL_BUILD_SHA||process.env.VERCEL_GIT_COMMIT_SHA||'';
if(!revision){
 try{
  const dirty=execFileSync('git',['status','--porcelain'],{encoding:'utf8'}).trim();
  if(!dirty)revision=execFileSync('git',['rev-parse','HEAD'],{encoding:'utf8'}).trim();
 }catch{/* Uncommitted local builds must not claim to be the committed release. */}
}
if(!/^[a-f0-9]{40}$/i.test(revision))revision='unknown';
if(process.env.VERCEL&&revision==='unknown')throw new Error('A deployment requires REHEARSAL_BUILD_SHA or VERCEL_GIT_COMMIT_SHA.');
export default {env:{NEXT_PUBLIC_BUILD_SHA:revision}};
