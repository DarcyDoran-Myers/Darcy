// usage: node video.js <format> <out.mp4|stills> [frames,...]
const {chromium}=require('playwright');const fs=require('fs');const {spawn}=require('child_process');
const N='/tmp/claude-0/-home-user-Darcy/c2bff291-be31-54b8-be92-bb527f50778d/scratchpad/work/node/node_modules/';
const D='/home/user/Darcy/florida-conservation/';
const FONTS={'barlow-600':'@fontsource/barlow-semi-condensed/files/barlow-semi-condensed-latin-600-normal.woff2','barlow-700':'@fontsource/barlow-semi-condensed/files/barlow-semi-condensed-latin-700-normal.woff2','public-400':'@fontsource/public-sans/files/public-sans-latin-400-normal.woff2','public-600':'@fontsource/public-sans/files/public-sans-latin-600-normal.woff2'};
const [fmt,out,list]=process.argv.slice(2);
(async()=>{const b=await chromium.launch();const p=await b.newPage({viewport:{width:1080,height:1920}});
p.on('pageerror',e=>console.log('ERR',e.message));p.on('console',m=>m.type()==='error'&&console.log(m.text()));
await p.route('http://v.test/**',r=>{const u=new URL(r.request().url()).pathname;
 if(u.endsWith('d3.min.js'))return r.fulfill({path:N+'d3/dist/d3.min.js'});
 if(u.endsWith('topojson-client.min.js'))return r.fulfill({path:N+'topojson-client/dist/topojson-client.min.js'});
 const m=u.match(/fonts\/(.+)\.woff2$/); if(m)return r.fulfill({path:N+FONTS[m[1]],contentType:'font/woff2'});
 if(u.endsWith('lands.json')||u.endsWith('meta.json')||u.endsWith('developed.bin'))return r.fulfill({path:D+u.split('/').pop()});
 return r.fulfill({path:D+'video/render.html',contentType:'text/html'});});
await p.goto('http://v.test/video/render.html');
const n=await p.evaluate(f=>window.setup(f),fmt); console.log('frames',n);
const grab=async i=>Buffer.from((await p.evaluate(i=>{renderFrame(i);return document.getElementById('c').toDataURL('image/png').split(',')[1];},i)),'base64');
if(out==='stills'){ for(const i of list.split(',').map(Number)) fs.writeFileSync(`/tmp/claude-0/-home-user-Darcy/c2bff291-be31-54b8-be92-bb527f50778d/scratchpad/${fmt}-${i}.png`,await grab(i)); }
else {
 const ff=spawn('ffmpeg',['-y','-loglevel','error','-f','image2pipe','-framerate','30','-i','-','-c:v','libx264','-pix_fmt','yuv420p','-crf','19','-preset','medium','-movflags','+faststart',out],{stdio:['pipe','inherit','inherit']});
 for(let i=0;i<n;i++){ const buf=await grab(i); if(!ff.stdin.write(buf)) await new Promise(r=>ff.stdin.once('drain',r)); if(i%150===0)console.log(i); }
 ff.stdin.end(); await new Promise(r=>ff.on('close',r));
}
await b.close();})();
