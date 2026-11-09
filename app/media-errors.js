export function microphoneError(error) {
  if(error.name==='NotAllowedError')return 'Microphone permission was denied. Upload a recording or type instead.';
  if(error.name==='NotFoundError'||error.name==='DevicesNotFoundError')return 'No microphone was found. Connect a microphone, upload a recording, or type instead.';
  return error.message||'Voice mode stopped. Check your connection and try again.';
}
