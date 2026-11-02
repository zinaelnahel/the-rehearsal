// Original decorative production icons; the adjacent step labels supply the text.
export default function FilmIcon({step}) {
 const drawings=[
  <g key="script"><path d="M7 3h10a2 2 0 0 1 2 2v16H7a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2Z"/><path d="M9 7h6M9 11h6M9 15h4M5 17h14"/></g>,
  <g key="storyboard"><rect x="3" y="4" width="18" height="16" rx="1"/><path d="M3 12h18M12 4v16M6 8h3M15 8h3M6 16h3M15 16h3"/></g>,
  <g key="clapperboard"><path d="M3 10h18v10H3zM3 10 2 5l17-3 1 5-17 3ZM7 4l3 4M13 3l3 4M7 14h10"/></g>,
  <g key="reel"><circle cx="12" cy="11" r="8"/><circle cx="12" cy="11" r="1"/><circle cx="12" cy="6.5" r="1.5"/><circle cx="16" cy="12.5" r="1.5"/><circle cx="8" cy="12.5" r="1.5"/><path d="M12 19h8l2 2"/></g>
 ];
 return <svg className="film-icon" viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" focusable="false">{drawings[step]}</svg>;
}
