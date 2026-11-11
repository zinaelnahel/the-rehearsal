'use client';
import {createContext,useContext,useEffect,useState} from 'react';
import {usePathname} from 'next/navigation';
import RehearsalApp from './RehearsalApp';

const Visited=createContext(false);
export function useVisitedRehearsal(){return useContext(Visited);}

export default function RehearsalWorkspace({children}){
 const pathname=usePathname();
 const active=pathname==='/';
 const [visited,setVisited]=useState(active);
 useEffect(()=>{if(active)setVisited(true);},[active]);
 // Keep the rehearsal mounted during same-tab navigation. Direct About visits
 // do not start a session or connect to the practice API.
 return <Visited.Provider value={visited}>
  {(visited||active)&&<div className="rehearsal-workspace" hidden={!active}><RehearsalApp active={active}/></div>}
  {children}
 </Visited.Provider>;
}
