const assert=require('node:assert/strict');
const fs=require('fs');
const vm=require('vm');
const crypto=require('node:crypto');
const src=fs.readFileSync('js/main.min.js','utf8');
const login=fs.readFileSync('login.html','utf8');
const index=fs.readFileSync('index.html','utf8');
function section(a,b){const start=src.indexOf(a),end=src.indexOf(b,start);assert(start>=0&&end>start,a);return src.slice(start,end);}
const ctx={decodeURIComponent,encodeURIComponent,String,RegExp,Number,Date,Math,isFinite,Array};
vm.createContext(ctx);
vm.runInContext(section('function decodeHotspotError(','function onLoginStart('),ctx);
for (const input of ['request failed: 504','unexpected gateway response','other unrecognized failure']) {
 const result=ctx.classifyHotspotError(input,false);
 assert.notEqual(result.message,'الكرت خطأ، حاول بكرت آخر',input);
 assert.equal(result.confirmed,false,input);
}
assert.equal(ctx.classifyHotspotError('user not found',false).code,'USER_NOT_FOUND');
assert.equal(ctx.classifyHotspotError('RADIUS timeout',false).code,'AUTH_SERVER_UNAVAILABLE');
assert.equal(ctx.classifyHotspotError('radius reject',false).credentialFailure,false);
assert(!/primeSpeedSignal\(getChosenSpeed\(\)\)/.test(src),'Duplicate speed pulse on change');
assert(/function handleNegativeStatus\(/.test(src),'Negative status must be confirmed before switching');
assert(/pendingRememberUsername/.test(src),'Require username match before saving card');
assert(/request\.open\(postFields \? 'POST' : 'GET'/.test(src),'Card numbers must not be sent in login query URL');
assert(!/['"]\/login\?username=/.test(src),'No credential-bearing login query strings');
assert(login.includes('$(if var == "native")'),'RouterOS native fallback missing');
assert(index.includes('/login?var=native'),'Fallback must be accessible even without JS');
assert(src.includes('var nativeLoginLink = document.querySelector'), 'Selected speed should transfer through the visible native link');
assert(index.includes('logo-fallback.png'),'Old browser fallback image missing');
assert(!/3600 requests/.test(src));
const mock={loggedIn:true,lastLoginAt:0,sessionNegativeCount:0,sessionNegativeAt:0,
  when:10000, ended:0, delays:[],Date:{now(){return mock.when}},
  onSessionEnded(){mock.ended++;},scheduleStatusQuery(delay){mock.delays.push(delay)}};
vm.createContext(mock);
vm.runInContext(section('function parseRouterTimeSeconds(', 'function onStatusQuery('),mock);
assert.equal(mock.parseRouterTimeSeconds('1h2m3s'),3723);
assert.equal(mock.parseRouterTimeSeconds('00:15'),15);
mock.handleNegativeStatus();assert.equal(mock.ended,0);assert.equal(mock.delays[0],2000);
mock.when=12100;mock.handleNegativeStatus();assert.equal(mock.ended,1,'Require confirmation of session loss');

const hash=require('../js/md5.js');
for(const val of ['','abc','message digest','abc123\x01\xFF']){
 const expected=crypto.createHash('md5').update(Buffer.from(val,'latin1')).digest('hex');
 assert.equal(hash(val),expected,'MD5 RFC vector / CHAP');
}
console.log('PASS deep regression: errors, POST, native CHAP, logo, speed, session guards and MD5');
