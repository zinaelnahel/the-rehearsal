import test from 'node:test';
import assert from 'node:assert/strict';
import {videoEvidence,youtubeId,videoTime} from '../app/video-evidence.mjs';

test('source timestamps open the original video section without inventing times',()=>{
 const result=videoEvidence({url:'https://www.youtube.com/watch?v=8YsZZpFW_QU',start:79.27,end:85.25});
 assert.equal(result.external,'https://www.youtube.com/watch?v=8YsZZpFW_QU&t=79s');
 assert.equal(new URL(result.embed).searchParams.get('start'),'79');
 assert.equal(new URL(result.embed).searchParams.get('end'),'86');
 assert.equal(new URL(result.embed).hostname,'www.youtube-nocookie.com');
 assert.equal(videoTime(79.27),'1:19');
 assert.equal(videoEvidence({url:'https://youtu.be/8YsZZpFW_QU'}).timed,false);
 assert.equal(videoEvidence({url:'https://youtu.be/8YsZZpFW_QU',start:-1}).timed,false);
});

test('only supported YouTube URLs can become embedded players',()=>{
 for(const url of ['javascript:alert(1)','https://youtube.com.evil.test/watch?v=8YsZZpFW_QU','https://user@youtube.com/watch?v=8YsZZpFW_QU','https://example.com/video.mp4'])assert.equal(videoEvidence({url}),null);
 assert.equal(youtubeId('https://youtu.be/8YsZZpFW_QU'),'8YsZZpFW_QU');
 assert.equal(youtubeId('https://www.youtube.com/shorts/8YsZZpFW_QU'),'8YsZZpFW_QU');
});
